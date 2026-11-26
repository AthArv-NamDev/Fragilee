"""Prove local issuer tokens use only the verifier paths already supported by Fragilee."""
import time

import jwt

from app import auth, settings
from conftest import KID, USER_A, make_token


LOCAL_URL = "http://127.0.0.1:54321"


def test_local_hs256_jwt_works_only_with_local_secret(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_URL", LOCAL_URL)
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "local-jwt-secret-for-tests-only-32-bytes")
    now = int(time.time())
    token = jwt.encode({
        "sub": USER_A, "aud": "authenticated", "iss": f"{LOCAL_URL}/auth/v1", "role": "authenticated",
        "iat": now, "exp": now + 300,
    }, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
    assert auth.verify_token(token)["sub"] == USER_A


def test_local_asymmetric_jwt_uses_local_auth_jwks(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_URL", LOCAL_URL)
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "")
    monkeypatch.setattr(auth, "_jwk_client", type("LocalJWKS", (), {
        "get_signing_key_from_jwt": lambda self, token: __import__("conftest").StubJWKS().get_signing_key_from_jwt(token),
    })())
    token = make_token(iss=f"{LOCAL_URL}/auth/v1", kid=KID)
    assert auth.verify_token(token)["sub"] == USER_A
