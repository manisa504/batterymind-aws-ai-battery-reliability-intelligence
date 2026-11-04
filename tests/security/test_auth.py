"""Authentication and input-validation security tests (spec §14).

A locally generated RSA key stands in for the Cognito signing key, so these tests exercise the real
verification code path (signature, algorithm, issuer, audience, expiry, token_use) without AWS.
"""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.api import auth, main
from apps.api.settings import Settings

POOL, CLIENT, REGION = "us-east-2_TESTPOOL", "test-client-id", "us-east-2"
ISSUER = f"https://cognito-idp.{REGION}.amazonaws.com/{POOL}"
SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _Key:
    key = SIGNING_KEY.public_key()


class _FakeJwks:
    def get_signing_key_from_jwt(self, token):
        return _Key()


@pytest.fixture(autouse=True)
def cognito(monkeypatch):
    monkeypatch.setattr(auth.settings, "cognito_user_pool_id", POOL)
    monkeypatch.setattr(auth.settings, "cognito_client_id", CLIENT)
    monkeypatch.setattr(auth.settings, "aws_region", REGION)
    monkeypatch.setattr(auth.settings, "local_auth_enabled", False)
    monkeypatch.setattr(auth, "_cognito_jwks_client", lambda region, pool: _FakeJwks())


def token(key=SIGNING_KEY, algorithm="RS256", **overrides):
    claims = {"sub": "user-1", "aud": CLIENT, "iss": ISSUER, "token_use": "id", "exp": int(time.time()) + 300}
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm=algorithm)


client = TestClient(main.app)


def status(bearer):
    headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}
    return client.get("/api/v1/usage", headers=headers).status_code


def test_valid_cognito_id_token_is_accepted():
    assert status(token()) == 200


@pytest.mark.parametrize(
    "forged",
    [
        pytest.param(lambda: token(key=OTHER_KEY), id="signed-by-another-key"),
        pytest.param(lambda: token(exp=int(time.time()) - 10), id="expired"),
        pytest.param(lambda: token(aud="another-client"), id="wrong-audience"),
        pytest.param(lambda: token(iss="https://cognito-idp.us-east-2.amazonaws.com/other"), id="wrong-issuer"),
        pytest.param(lambda: token(token_use="access"), id="access-token-not-id-token"),
        pytest.param(lambda: token(sub=None), id="missing-subject"),
        pytest.param(
            lambda: jwt.encode(
                {"sub": "user-1", "aud": CLIENT, "iss": ISSUER, "token_use": "id", "exp": int(time.time()) + 300},
                None,
                algorithm="none",
            ),
            id="alg-none",
        ),
        pytest.param(
            lambda: jwt.encode(
                {"sub": "user-1", "aud": CLIENT, "iss": ISSUER, "token_use": "id", "exp": int(time.time()) + 300},
                "shared-secret",
                algorithm="HS256",
            ),
            id="hs256-confusion",
        ),
        pytest.param(lambda: "not.a.jwt", id="garbage"),
    ],
)
def test_forged_or_invalid_tokens_are_rejected(forged):
    assert status(forged()) == 401


def test_impersonation_header_is_ignored_when_local_auth_is_disabled():
    response = client.get("/api/v1/usage", headers={"X-BatteryMind-User": "victim"})
    assert response.status_code == 401


def test_every_memory_route_requires_authentication():
    protected = [
        r
        for r in main.app.routes
        if isinstance(r, APIRoute) and any(d.call is auth.current_principal for d in r.dependant.dependencies)
    ]
    assert len(protected) >= 8
    for route in protected:
        path = route.path.replace("{battery_id}", "B0005").replace("{session_id}", "s").replace("{assessment_id}", "a")
        for method in route.methods:
            response = client.request(method, path, json={})
            assert response.status_code == 401, (method, path, response.status_code)


def test_local_auth_cannot_be_enabled_outside_local_environment():
    with pytest.raises(ValidationError):
        Settings(environment="production", local_auth_enabled=True)
    assert Settings(environment="production").local_auth_enabled is False


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/batteries/B0005/analysis?cutoff=0",
        "/api/v1/batteries/B0005/analysis?cutoff=-5",
        "/api/v1/batteries/B0005/analysis?cutoff=abc",
    ],
)
def test_invalid_query_input_is_rejected(path):
    assert client.get(path).status_code == 422


def test_invalid_bodies_are_rejected_before_any_work():
    bearer = {"Authorization": f"Bearer {token()}"}
    bad_battery = client.post("/api/v1/sessions", headers=bearer, json={"battery_id": "../etc", "objective": "x"})
    assert bad_battery.status_code == 422
    too_long = client.post("/api/v1/chat", headers=bearer, json={"session_id": "s", "message": "x" * 1001})
    assert too_long.status_code == 422
    empty = client.post("/api/v1/chat", headers=bearer, json={"session_id": "s", "message": ""})
    assert empty.status_code == 422


def test_cors_rejects_unknown_origins():
    response = client.options(
        "/api/v1/chat", headers={"Origin": "https://attacker.example", "Access-Control-Request-Method": "POST"}
    )
    assert "access-control-allow-origin" not in response.headers
