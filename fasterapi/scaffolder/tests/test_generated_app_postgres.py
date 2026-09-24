"""End-to-end checks of a generated project's auth and permissions on Postgres and Redis."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import uuid
from pathlib import Path

import pytest
from click.testing import CliRunner

from fasterapi.cli import cli

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
REDIS_URL = os.getenv("TEST_REDIS_URL")

pytestmark = pytest.mark.skipif(
    not (DATABASE_URL and REDIS_URL), reason="set TEST_DATABASE_URL and TEST_REDIS_URL to run end-to-end tests"
)

AUTH_FLOW = """
from fastapi.testclient import TestClient
import main
from core.database import db

def token(response):
    return {"Authorization": "Bearer " + response.json()["data"]["access_token"]}

with TestClient(main.app) as client:
    body = {"firstName": "A", "lastName": "B", "loginType": "EMAIL", "email": "a@x.com", "password": "pw-123456"}
    assert client.post("/v1/{plural}/signup", json=body).status_code == 201
    headers = token(client.post("/v1/{plural}/login", json=body))
    assert client.get("/v1/{plural}/me", headers=headers).status_code == 200
    assert client.get("/v1/{plural}/", headers=headers).status_code == 403

    attacker = dict(body, email="e@x.com", accountStatus="SUSPENDED",
                    permissionList={"permissions": [{"name": "list_{plural}", "methods": ["GET"], "path": "/v1/{plural}/"}]})
    assert client.post("/v1/{plural}/signup", json=attacker).status_code == 201
    stored = client.portal.call(lambda: db["{plural}"].find_one({"email": "e@x.com"}))
    assert [p["key"] for p in stored["permissionList"]["permissions"]] == ["GET:/v1/{plural}/me", "DELETE:/v1/{plural}/account"]
    assert stored["accountStatus"] == "ACTIVE"
    assert client.get("/v1/{plural}/", headers=token(client.post("/v1/{plural}/login", json=attacker))).status_code == 403

    assert client.delete("/v1/{plural}/account", headers=headers).status_code == 200

    root = token(client.post("/v1/admins/login", json={"email": "root@example.com", "password": "root-password-for-tests"}))
    assert client.get("/v1/admins/profile", headers=root).status_code == 200
    invite = {"full_name": "Ops", "email": "ops-{plural}@x.com", "password": "pw-123456"}
    assert client.post("/v1/admins/signup", json=invite, headers=root).status_code == 201
print("ok")
"""


AUTH_SECURITY_FLOW = """
import jwt
from fastapi.testclient import TestClient
import main
import services.user_service as user_service
from core.database import db
from schemas.user_schema import UserUpdate

def body(email, password="pw-123456", login_type="EMAIL"):
    return {"firstName": "A", "lastName": "B", "loginType": login_type, "email": email, "password": password}

with TestClient(main.app) as client:
    client.post("/v1/users/signup", json=body("a@x.com"))
    data = client.post("/v1/users/login", json=body("a@x.com")).json()["data"]
    auth = {"Authorization": "Bearer " + data["access_token"]}
    raw_id = jwt.decode(data["access_token"], options={"verify_signature": False})["accessToken"]
    assert client.get("/v1/users/me", headers={"Authorization": "Bearer " + raw_id}).status_code == 401

    assert client.post("/v1/users/signup", json=body("s@x.com", "short")).status_code == 422
    client.post("/v1/users/signup", json=body("claims-google@x.com", login_type="GOOGLE"))
    assert client.portal.call(lambda: db.users.find_one({"email": "claims-google@x.com"}))["loginType"] == "EMAIL"

    async def google_returns(info):
        async def authorize_access_token(request):
            return {"userinfo": info}
        user_service.oauth.google.authorize_access_token = authorize_access_token

    def callback(info):
        client.portal.call(google_returns, info)
        return client.get("/v1/users/auth/callback", follow_redirects=False).headers["location"]

    assert callback({"email": "g@gmail.com", "email_verified": False}).endswith("error=email_not_verified")
    location = callback({"email": "g@gmail.com", "email_verified": True})
    assert "#access_token=" in location and "?access_token" not in location
    assert callback({"email": "a@x.com", "email_verified": True}).endswith("error=account_exists")
    assert client.post("/v1/users/login", json=body("g@gmail.com", "")).status_code == 401

    client.post("/v1/users/signup", json=body("victim@x.com"))
    victim = client.post("/v1/users/login", json=body("victim@x.com")).json()["data"]
    assert client.post("/v1/users/refresh", json={"refresh_token": victim["refresh_token"]}, headers=auth).status_code == 404
    assert client.post("/v1/users/refresh", json={"refresh_token": "not-an-id"}, headers=auth).status_code == 404
    victim_auth = {"Authorization": "Bearer " + victim["access_token"]}
    assert client.post("/v1/users/refresh", json={"refresh_token": victim["refresh_token"]}, headers=victim_auth).status_code == 200

    user_id = str(client.portal.call(lambda: db.users.find_one({"email": "a@x.com"}))["_id"])
    client.portal.call(user_service.update_user_by_id, user_id, UserUpdate(), True)
    assert client.get("/v1/users/me", headers=auth).status_code == 401
print("ok")
"""

ACCOUNT_ADMIN_FLOW = """
from fastapi.testclient import TestClient
import main

def bearer(response):
    return {"Authorization": "Bearer " + response.json()["data"]["access_token"]}

with TestClient(main.app) as client:
    root = bearer(client.post("/v1/admins/login", json={"email": "root@example.com", "password": "root-password-for-tests"}))
    body = {"firstName": "A", "lastName": "B", "loginType": "EMAIL", "email": "a@x.com", "password": "pw-123456"}
    client.post("/v1/{plural}/signup", json=body)
    user = bearer(client.post("/v1/{plural}/login", json=body))
    role = "{plural}"[:-1]

    accounts = client.get(f"/v1/admins/accounts/{role}", headers=root).json()["data"]
    assert len(accounts) == 1 and "password" not in accounts[0]
    grantable = client.get(f"/v1/admins/accounts/{role}/permissions", headers=root).json()["data"]["permissions"]
    wanted = [p for p in grantable if p["name"] in ("list_users", "get_my_users")]
    assert client.get("/v1/{plural}/", headers=user).status_code == 403
    update = f"/v1/admins/accounts/{role}/{accounts[0]['id']}"
    assert client.patch(update, headers=root, json={"permissionList": {"permissions": wanted}}).status_code == 200
    assert client.get("/v1/{plural}/", headers=user).status_code == 200
    admin_only = {"name": "list_admins", "methods": ["GET"], "path": "/v1/admins", "key": "GET:/v1/admins"}
    assert client.patch(update, headers=root, json={"permissionList": {"permissions": [admin_only]}}).status_code == 400
    assert client.patch(update, headers=root, json={"accountStatus": "SUSPENDED"}).status_code == 200
    assert client.get("/v1/{plural}/me", headers=user).status_code == 401
    assert client.get("/v1/admins/accounts/admin", headers=root).status_code == 404
print("ok")
"""

def _project(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.chdir(tmp_path)
    assert CliRunner().invoke(cli, ["new", "app", "--db", "postgres"]).exit_code == 0
    project = tmp_path / "app"
    schema = f"s_{uuid.uuid4().hex[:10]}"
    url = f"{DATABASE_URL}{'&' if '?' in DATABASE_URL else '?'}options=-csearch_path%3D{schema}"
    subprocess.run([sys.executable, "-c", textwrap.dedent(f"""
        import asyncio, asyncpg
        async def main():
            conn = await asyncpg.connect({DATABASE_URL!r})
            await conn.execute('CREATE SCHEMA "{schema}"')
            await conn.close()
        asyncio.run(main())
    """)], check=True)
    env = (project / ".env.example").read_text()
    env += f"\nDATABASE_URL={url}\nREDIS_URL={REDIS_URL}\nENABLE_SCHEDULER=false\n"
    env += "SUPER_ADMIN_EMAIL=root@example.com\nSUPER_ADMIN_PASSWORD=root-password-for-tests\n"
    # Every test client shares one address, so the default anonymous limit would trip across tests.
    env += "ROLE_RATE_LIMITS=" + ",".join(f"{r}:10000/minute" for r in ("anonymous", "user", "driver", "rider", "customer", "admin")) + "\n"
    (project / ".env").write_text(env)
    return project


def _run_flow(project: Path, plural: str, script: str = AUTH_FLOW) -> None:
    completed = subprocess.run(
        [sys.executable, "-c", script.replace("{plural}", plural)], cwd=project, capture_output=True, text=True
    )
    assert completed.returncode == 0 and "ok" in completed.stdout, completed.stderr[-3000:]


def test_new_users_get_self_service_permissions_only(tmp_path, monkeypatch):
    _run_flow(_project(tmp_path, monkeypatch), "users")


def test_split_roles_get_their_own_default_permissions(tmp_path, monkeypatch):
    project = _project(tmp_path, monkeypatch)
    monkeypatch.chdir(project)
    assert CliRunner().invoke(cli, ["split-user"], input="driver\nrider\nend\n").exit_code == 0
    _run_flow(project, "drivers")


def test_make_account_roles_work_before_and_after_split(tmp_path, monkeypatch):
    project = _project(tmp_path, monkeypatch)
    monkeypatch.chdir(project)
    assert CliRunner().invoke(cli, ["make-account", "customer"]).exit_code == 0
    _run_flow(project, "customers")
    assert CliRunner().invoke(cli, ["split-user"], input="driver\nrider\nend\n").exit_code == 0
    _run_flow(project, "drivers")


def test_tokens_passwords_and_google_sign_in_are_not_bypassable(tmp_path, monkeypatch):
    _run_flow(_project(tmp_path, monkeypatch), "users", script=AUTH_SECURITY_FLOW)


def test_admins_can_list_grant_and_suspend_accounts(tmp_path, monkeypatch):
    project = _project(tmp_path, monkeypatch)
    _run_flow(project, "users", script=ACCOUNT_ADMIN_FLOW)
    monkeypatch.chdir(project)
    assert CliRunner().invoke(cli, ["make-account", "customer"]).exit_code == 0
    _run_flow(project, "customers", script=ACCOUNT_ADMIN_FLOW)
