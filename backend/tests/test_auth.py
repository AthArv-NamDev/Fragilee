"""Login checks and rate limits. Every bad token must get a plain 401 and nothing else."""
import base64
import hashlib
import hmac
import json
import time
import uuid

import jwt
import pytest

from app import auth, settings
from conftest import ISSUER, KID, USER_A, USER_B, headers_for, make_token, other_key_token

STAGE2_OK = {"category": "software", "state": "CA", "funding_total_usd": 250000, "funding_rounds": 2,
             "has_VC": False, "has_angel": True, "has_roundA": True, "has_roundB": False, "has_roundC": False,
             "has_roundD": False, "avg_participants": 2.0, "relationships": 5,
             "age_first_funding_year": 1.0, "age_last_funding_year": 2.0}
PROTECTED = [("post", "/v1/predict/stage2", STAGE2_OK), ("post", "/v1/analyses", {}), ("get", "/v1/analyses", None),
             ("get", f"/v1/analyses/{uuid.uuid4()}", None), ("delete", f"/v1/analyses/{uuid.uuid4()}", None)]


def _payload(**over):
    now = int(time.time())
    p = {"sub": USER_A, "aud": "authenticated", "iss": ISSUER, "role": "authenticated", "iat": now, "exp": now + 3600}
    p.update(over)
    return {k: v for k, v in p.items() if v is not None}


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _hs256(payload, secret):
    head = _b64(json.dumps({"alg": "HS256", "typ": "JWT", "kid": KID}).encode())
    body = _b64(json.dumps(payload).encode())
    sig = hmac.new(secret, f"{head}.{body}".encode(), hashlib.sha256).digest()
    return f"{head}.{body}.{_b64(sig)}"


def test_public_routes_need_no_login(anon_client):
    assert anon_client.get("/health").status_code == 200
    assert anon_client.get("/v1/meta").status_code == 200


@pytest.mark.parametrize("method,path,body", PROTECTED)
def test_protected_routes_refuse_missing_token(anon_client, method, path, body):
    r = getattr(anon_client, method)(path, **({"json": body} if body is not None else {}))
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


def _bad_tokens():
    good = make_token()
    head, body, sig = good.split(".")
    forged_body = _b64(json.dumps(_payload(sub=USER_B)).encode())
    from conftest import PUBLIC_PEM
    return {
        "garbage": "not-a-token",
        "expired": make_token(exp=int(time.time()) - 120),
        "wrong audience": make_token(aud="somebody-else"),
        "wrong issuer": make_token(iss="https://evil.example/auth/v1"),
        "anon role (the public key is a token too)": make_token(role="anon"),
        "no subject": jwt.encode({k: v for k, v in _payload().items() if k != "sub"}, __import__("conftest")._private,
                                 algorithm="ES256", headers={"kid": KID}),
        "subject is not a uuid": make_token("not-a-uuid"),
        "unknown key id": make_token(kid="not-our-key"),
        "signed by a different key": other_key_token(),
        "payload swapped, old signature": f"{head}.{forged_body}.{sig}",
        "alg none": jwt.encode(_payload(), key=None, algorithm="none"),
        "HS256 signed with the public key (algorithm confusion)": _hs256(_payload(), PUBLIC_PEM),
        "HS256 with a guessed secret": _hs256(_payload(), b"secret"),
        "oversized": "a" * 5000,
    }


@pytest.mark.parametrize("label", list(_bad_tokens()))
def test_bad_tokens_get_401(anon_client, label):
    token = _bad_tokens()[label]
    r = anon_client.post("/v1/predict/stage2", json=STAGE2_OK, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401, label
    assert token not in r.text            # we never echo the token back


def test_small_clock_difference_is_tolerated_but_not_a_big_one(anon_client):
    soon = {"Authorization": f"Bearer {make_token(iat=int(time.time()) + 5)}"}        # issued "5 seconds from now"
    far = {"Authorization": f"Bearer {make_token(iat=int(time.time()) + 300)}"}       # 5 minutes in the future
    assert anon_client.post("/v1/predict/stage2", json=STAGE2_OK, headers=soon).status_code == 200
    assert anon_client.post("/v1/predict/stage2", json=STAGE2_OK, headers=far).status_code == 401


def test_rejection_reason_is_logged_without_the_token(anon_client, caplog):
    token = make_token(iss="https://evil.example/auth/v1")
    with caplog.at_level("WARNING", logger="fragilee.auth"):
        anon_client.post("/v1/predict/stage2", json=STAGE2_OK, headers={"Authorization": f"Bearer {token}"})
    assert "InvalidIssuerError" in caplog.text
    assert token not in caplog.text and token.split(".")[1] not in caplog.text


def test_wrong_scheme_is_refused(anon_client):
    r = anon_client.post("/v1/predict/stage2", json=STAGE2_OK, headers={"Authorization": "Basic abc"})
    assert r.status_code == 401


def test_good_token_works(anon_client):
    assert anon_client.post("/v1/predict/stage2", json=STAGE2_OK, headers=headers_for(USER_A)).status_code == 200


def test_legacy_hs256_only_when_a_secret_is_configured(anon_client, monkeypatch):
    token = _hs256(_payload(), b"legacy-secret")
    h = {"Authorization": f"Bearer {token}"}
    assert anon_client.post("/v1/predict/stage2", json=STAGE2_OK, headers=h).status_code == 401
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "legacy-secret")
    assert anon_client.post("/v1/predict/stage2", json=STAGE2_OK, headers=h).status_code == 200
    bad = {"Authorization": f"Bearer {_hs256(_payload(), b'wrong')}"}
    assert anon_client.post("/v1/predict/stage2", json=STAGE2_OK, headers=bad).status_code == 401


@pytest.mark.skipif(not auth.PyJWKClientConnectionError, reason="needs a newer PyJWT")
def test_key_endpoint_outage_is_503_not_a_free_pass(anon_client, monkeypatch):
    class Down:
        def get_signing_key_from_jwt(self, token):
            raise auth.PyJWKClientConnectionError("down")
    monkeypatch.setattr(auth, "_jwk_client", Down())
    r = anon_client.post("/v1/predict/stage2", json=STAGE2_OK, headers=headers_for(USER_A))
    assert r.status_code == 503


def test_cors_allows_only_the_configured_origin(anon_client):
    ok = anon_client.options("/v1/meta", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    bad = anon_client.options("/v1/meta", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "access-control-allow-origin" not in bad.headers


# ---- rate limits ---------------------------------------------------------------
def test_per_user_limit_is_per_user(anon_client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_PREDICT", "2/minute")
    post = lambda sub: anon_client.post("/v1/predict/stage2", json=STAGE2_OK, headers=headers_for(sub))
    assert [post(USER_A).status_code for _ in range(2)] == [200, 200]
    blocked = post(USER_A)
    assert blocked.status_code == 429 and int(blocked.headers["retry-after"]) >= 1
    assert post(USER_B).status_code == 200            # someone else is unaffected


def test_ip_limit_throttles_even_bad_tokens(anon_client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_IP", "3/minute")
    codes = [anon_client.post("/v1/predict/stage2", json=STAGE2_OK,
                              headers={"Authorization": "Bearer junk"}).status_code for _ in range(5)]
    assert codes == [401, 401, 401, 429, 429]


def test_reads_have_their_own_limit(anon_client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_READ", "2/minute")
    codes = [anon_client.get("/v1/analyses", headers=headers_for(USER_A)).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
