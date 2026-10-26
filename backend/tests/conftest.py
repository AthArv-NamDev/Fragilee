"""Shared test setup: fake Supabase keys, in-memory storage, and token helpers."""
import os
import time
import uuid
from types import SimpleNamespace

# These must be set BEFORE the app is imported. They override whatever is in your shell.
os.environ.update({
    "SUPABASE_URL": "https://test.supabase.co", "SUPABASE_ANON_KEY": "anon-test-key", "STORAGE": "memory",
    "ENV": "dev", "ALLOWED_ORIGINS": "http://localhost:3000", "FREE_ANALYSIS_LIMIT": "0",
    "RATE_LIMIT_PREDICT": "1000/minute", "RATE_LIMIT_READ": "1000/minute", "RATE_LIMIT_IP": "100000/minute",
})

import jwt  # noqa: E402
import pytest  # noqa: E402
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import auth, settings  # noqa: E402
from app.limits import limiter  # noqa: E402
from app.main import app  # noqa: E402

KID = "test-key-1"
_private = ec.generate_private_key(ec.SECP256R1())
_other_private = ec.generate_private_key(ec.SECP256R1())
PUBLIC_KEY = _private.public_key()
PUBLIC_PEM = PUBLIC_KEY.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
USER_A, USER_B = str(uuid.uuid4()), str(uuid.uuid4())
ISSUER = "https://test.supabase.co/auth/v1"


class StubJWKS:
    """Stands in for Supabase's public key list."""
    def get_signing_key_from_jwt(self, token):
        if jwt.get_unverified_header(token).get("kid") != KID:
            raise jwt.PyJWKClientError("Unable to find a signing key that matches")
        return SimpleNamespace(key=PUBLIC_KEY)


def make_token(sub=None, *, key=None, alg="ES256", kid=KID, **claims):
    now = int(time.time())
    payload = {"sub": USER_A if sub is None else sub, "aud": "authenticated", "iss": ISSUER, "role": "authenticated",
               "iat": now, "exp": now + 3600, **claims}
    payload = {k: v for k, v in payload.items() if v is not None}
    return jwt.encode(payload, key or _private, algorithm=alg, headers={"kid": kid} if kid else None)


def other_key_token(**claims):
    return make_token(key=_other_private, **claims)


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    monkeypatch.setattr(auth, "_jwk_client", StubJWKS())
    monkeypatch.setattr(settings, "RATE_LIMIT_PREDICT", "1000/minute")
    monkeypatch.setattr(settings, "RATE_LIMIT_READ", "1000/minute")
    monkeypatch.setattr(settings, "RATE_LIMIT_IP", "100000/minute")
    monkeypatch.setattr(settings, "FREE_ANALYSIS_LIMIT", 0)
    limiter.reset()
    store = getattr(app.state, "analyses", None)
    if store is not None and hasattr(store, "_rows"):
        store._rows.clear()          # every test starts with an empty history


@pytest.fixture(scope="module")
def client():
    """A client that is signed in as user A."""
    with TestClient(app, headers={"Authorization": f"Bearer {make_token(USER_A)}"}) as c:
        yield c


@pytest.fixture(scope="module")
def anon_client():
    with TestClient(app) as c:
        yield c


def headers_for(sub):
    return {"Authorization": f"Bearer {make_token(sub)}"}
