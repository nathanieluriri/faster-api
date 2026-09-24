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

DOCUMENTS_FLOW = """
import os
from fastapi.testclient import TestClient
import main
import api.v1.documents_route as documents_route
from core.storage.manager import DocumentStorageManager

def login(client, email):
    body = {"firstName": "A", "lastName": "B", "loginType": "EMAIL", "email": email, "password": "pw-123456"}
    client.post("/v1/users/signup", json=body)
    return {"Authorization": "Bearer " + client.post("/v1/users/login", json=body).json()["data"]["access_token"]}

with TestClient(main.app) as client:
    root = DocumentStorageManager.get_instance().provider._root
    alice, bob = login(client, "a@x.com"), login(client, "b@x.com")
    intent = client.post("/v1/documents/upload-intents", headers=alice, json={"file_name": "r.pdf", "mime_type": "application/pdf", "size": 11}).json()["data"]
    key = intent["object_key"]
    assert client.post(f"/v1/documents/upload-local/{key}?expires=9999999999&signature=bad", files={"file": ("r.pdf", b"x")}).status_code == 403
    assert client.post(intent["upload_url"], files={"file": ("r.pdf", b"hello world")}).status_code == 204
    assert client.post("/v1/documents/complete", headers=bob, json={"object_key": key}).status_code == 404
    assert client.post("/v1/documents/complete", headers=alice, json={"object_key": "../../.env"}).status_code == 404
    done = client.post("/v1/documents/complete", headers=alice, json={"object_key": key, "size": 5}).json()["data"]
    assert done["size"] == 11 and done["status"] == "ready"
    assert client.post("/v1/documents/complete", headers=alice, json={"object_key": key}).status_code == 409
    doc_id = done.get("_id") or done.get("id")
    assert client.get(f"/v1/documents/{doc_id}", headers=bob).status_code == 403
    download = client.get(f"/v1/documents/{doc_id}", headers=alice).json()["data"]["download_url"]
    served = client.get(download)
    assert served.content == b"hello world" and served.headers["x-content-type-options"] == "nosniff"
    assert client.get(download[:-1] + ("0" if download[-1] != "0" else "1")).status_code == 403

    documents_route.MAX_UPLOAD_BYTES = 1024
    big = client.post("/v1/documents/upload-intents", headers=alice, json={"file_name": "b.bin", "mime_type": "application/octet-stream", "size": 10}).json()["data"]
    assert client.post(big["upload_url"], files={"file": ("b.bin", b"x" * 5000)}).status_code == 413
    assert not (root / big["object_key"]).exists()

    assert client.delete(f"/v1/documents/{doc_id}", headers=alice).status_code == 200
    assert not (root / key).exists()
print("ok")
"""

PAYMENTS_FLOW = """
import asyncio, hashlib, hmac, json, time
import stripe
from fastapi.testclient import TestClient
import main
import core.payments.flutterwave_provider as flw
import services.payment_service as payment_service
from schemas.payment_schema import PaymentIntentIn

sent, remote = [], {}

class FakeResponse:
    def __init__(self, data, status=200):
        self._data, self.status_code = data, status
    def json(self):
        return self._data

def fake_request(method, url, headers=None, timeout=None, json=None, params=None):
    sent.append((method, url, json))
    if url.endswith("/payments"):
        return FakeResponse({"status": "success", "data": {"link": "https://pay.example/x"}})
    if "verify_by_reference" in url:
        return FakeResponse({"status": "success", "data": remote[params["tx_ref"]]})
    return FakeResponse({"status": "success", "data": {"id": "refund-1"}})

flw.requests.request = fake_request
stripe_created = {}
def pi_create(**kwargs):
    stripe_created.update(kwargs)
    return stripe.PaymentIntent.construct_from({"id": "pi_123", "client_secret": "cs_1", "amount": kwargs["amount"], "currency": kwargs["currency"], "status": "requires_payment_method", "metadata": kwargs["metadata"]}, "sk")
stripe.PaymentIntent.create = pi_create
stripe.PaymentIntent.retrieve = lambda intent_id: stripe.PaymentIntent.construct_from({"id": intent_id, "status": "succeeded", "amount": 2500, "amount_received": 2500, "currency": "usd", "metadata": {"reference": "STRIPE-1"}}, "sk")
stripe.Refund.create = lambda **kwargs: stripe.Refund.construct_from({"id": "re_1", **kwargs}, "sk")

def login(client, email, admin=False):
    if admin:
        r = client.post("/v1/admins/login", json={"email": "root@example.com", "password": "root-password-for-tests"})
    else:
        body = {"firstName": "A", "lastName": "B", "loginType": "EMAIL", "email": email, "password": "pw-123456"}
        client.post("/v1/users/signup", json=body)
        r = client.post("/v1/users/login", json=body)
    return {"Authorization": "Bearer " + r.json()["data"]["access_token"]}

def flw_webhook(client, tx_id, reference, secret="flw-hash", body=None):
    payload = body if body is not None else json.dumps({"event": "charge.completed", "data": {"id": tx_id, "tx_ref": reference}})
    headers = {"verif-hash": secret} if secret else {}
    return client.post("/v1/payments/webhooks/flutterwave", content=payload, headers=headers)

def check(label, condition):
    assert condition, label

with TestClient(main.app) as client:
    alice, bob, admin = login(client, "a@x.com"), login(client, "b@x.com"), login(client, None, admin=True)
    intent = lambda headers, **kw: client.post("/v1/payments/intents", headers=headers, json={"amount_minor": 50000, "currency": "ngn", "provider": "flutterwave", **kw})

    r = intent(alice, reference="ORD-1")
    check("create intent", r.status_code == 201 and r.json()["data"]["currency"] == "NGN")
    check("NGN sent in major units", sent[-1][2]["amount"] == 500)
    intent(alice, reference="XAF-1", amount_minor=5000, currency="XAF")
    check("zero-decimal XAF not divided by 100", sent[-1][2]["amount"] == 5000)
    check("same reference by another user is refused", intent(bob, reference="ORD-1").status_code == 409)
    check("idempotent retry by the owner returns the payment", intent(alice, reference="ORD-1").status_code == 201)
    check("unsupported provider is a 400", intent(alice, reference="P-1", provider="paypal").status_code == 400)
    check("reference with quotes is rejected", intent(alice, reference="x' OR 'a").status_code == 422)

    async def race():
        body = PaymentIntentIn(amount_minor=100, currency="NGN", reference="RACE-1", provider="flutterwave")
        return await asyncio.gather(*(payment_service.create_payment_intent(owner_id=f"owner{i}", payload=body) for i in range(3)), return_exceptions=True)
    results = client.portal.call(race)
    check("concurrent intents with one reference create one payment", sum(not isinstance(r, Exception) for r in results) == 1)

    remote["ORD-1"] = {"id": 111, "status": "successful", "amount": 500, "currency": "NGN"}
    check("unsigned Flutterwave webhook is rejected", flw_webhook(client, 111, "ORD-1", secret=None).status_code == 401)
    check("wrong Flutterwave hash is rejected", flw_webhook(client, 111, "ORD-1", secret="nope").status_code == 401)
    check("non-JSON body is a 400", flw_webhook(client, 111, "ORD-1", body="not json").status_code == 400)
    r = flw_webhook(client, 111, "ORD-1")
    check("signed webhook marks the payment succeeded", r.status_code == 200 and r.json()["data"]["status"] == "succeeded")
    check("duplicate webhook is acknowledged, not reprocessed", flw_webhook(client, 111, "ORD-1").json()["data"].get("duplicate") is True)
    remote["XAF-1"] = {"id": 222, "status": "successful", "amount": 1, "currency": "XAF"}
    r = flw_webhook(client, 222, "XAF-1")
    check("a different payment's webhook still processes, underpayment marked failed", r.status_code == 200 and r.json()["data"]["status"] == "failed")

    stripe_intent = client.post("/v1/payments/intents", headers=alice, json={"amount_minor": 2500, "currency": "USD", "provider": "stripe", "reference": "STRIPE-1", "metadata": {"reference": "HIJACK"}})
    check("Stripe intent keeps the real reference", stripe_intent.status_code == 201 and stripe_created["metadata"]["reference"] == "STRIPE-1")
    event = json.dumps({"id": "evt_1", "object": "event", "type": "payment_intent.succeeded", "data": {"object": {"id": "pi_123", "object": "payment_intent", "metadata": {"reference": "STRIPE-1"}}}})
    stamp = int(time.time())
    signature = hmac.new(b"whsec_test", f"{stamp}.{event}".encode(), hashlib.sha256).hexdigest()
    r = client.post("/v1/payments/webhooks/Stripe", content=event, headers={"stripe-signature": f"t={stamp},v1={signature}"})
    check("signed Stripe webhook marks the payment succeeded", r.status_code == 200 and r.json()["data"]["status"] == "succeeded")

    pay_id = intent(alice, reference="ORD-1").json()["data"]["_id"]
    check("owner can't refund", client.post(f"/v1/payments/{pay_id}/refund", headers=alice, json={}).status_code == 403)
    check("over-refund is refused", client.post(f"/v1/payments/{pay_id}/refund", headers=admin, json={"amount_minor": 60000}).status_code == 400)
    r = client.post(f"/v1/payments/{pay_id}/refund", headers=admin, json={"amount_minor": 20000})
    check("partial refund keeps status succeeded", r.status_code == 200 and r.json()["data"]["status"] == "succeeded" and r.json()["data"]["refunded_minor"] == 20000)
    check("refund sent in major units", sent[-1][2] == {"amount": 200})
    r = client.post(f"/v1/payments/{pay_id}/refund", headers=admin, json={})
    check("refunding the rest marks it refunded", r.json()["data"]["status"] == "refunded" and r.json()["data"]["refunded_minor"] == 50000)
    r = client.post("/v1/payments/webhooks/flutterwave", content=json.dumps({"event": "charge.completed", "data": {"id": 999, "tx_ref": "ORD-1"}}), headers={"verif-hash": "flw-hash"})
    check("a late success webhook can't undo the refund", r.json()["data"]["status"] == "refunded")
print("ok")
"""

def _project(tmp_path: Path, monkeypatch, extra_env: str = "") -> Path:
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
    env += f"STORAGE_LOCAL_ROOT={tmp_path / 'uploads'}\n"
    env += extra_env
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


def test_document_uploads_are_signed_owned_and_size_limited(tmp_path, monkeypatch):
    _run_flow(_project(tmp_path, monkeypatch), "users", script=DOCUMENTS_FLOW)


def test_payments_are_owned_verified_and_forward_only(tmp_path, monkeypatch):
    keys = "FLUTTERWAVE_SECRET_KEY=flw-test\nFLW_WEBHOOK_SECRET_HASH=flw-hash\nSTRIPE_SECRET_KEY=sk_test_x\nSTRIPE_WEBHOOK_SECRET=whsec_test\n"
    _run_flow(_project(tmp_path, monkeypatch, extra_env=keys), "users", script=PAYMENTS_FLOW)
