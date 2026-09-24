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
    invite = {"full_name": "Ops", "email": "ops@x.com", "password": "pw-123456"}
    assert client.post("/v1/admins/signup", json=invite, headers=root).status_code == 201
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
    env += "ROLE_RATE_LIMITS=" + ",".join(f"{r}:10000/minute" for r in ("anonymous", "user", "driver", "rider", "admin")) + "\n"
    (project / ".env").write_text(env)
    return project


def _run_flow(project: Path, plural: str) -> None:
    completed = subprocess.run(
        [sys.executable, "-c", AUTH_FLOW.replace("{plural}", plural)], cwd=project, capture_output=True, text=True
    )
    assert completed.returncode == 0 and "ok" in completed.stdout, completed.stderr[-3000:]


def test_new_users_get_self_service_permissions_only(tmp_path, monkeypatch):
    _run_flow(_project(tmp_path, monkeypatch), "users")


def test_split_roles_get_their_own_default_permissions(tmp_path, monkeypatch):
    project = _project(tmp_path, monkeypatch)
    monkeypatch.chdir(project)
    assert CliRunner().invoke(cli, ["split-user"], input="driver\nrider\nend\n").exit_code == 0
    _run_flow(project, "drivers")
