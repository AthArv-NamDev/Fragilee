"""Checks the Supabase login token on every protected request.

The browser logs in with Supabase and sends its token as 'Authorization: Bearer <token>'.
We verify the signature against Supabase's public keys (JWKS), the expiry, the audience and the issuer.
The backend never sees a password and holds no secret key for this.
"""
import inspect
import logging
import uuid
from dataclasses import dataclass, field

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWKClientError

try:
    from jwt.exceptions import PyJWKClientConnectionError
except ImportError:                      # older PyJWT: connection problems arrive as PyJWKClientError
    PyJWKClientConnectionError = ()

from . import settings
from .limits import limiter

log = logging.getLogger("fragilee.auth")
bearer = HTTPBearer(auto_error=False, description="Supabase access token")
ASYMMETRIC = ("ES256", "RS256")      # what Supabase's public-key signing uses
MAX_TOKEN_CHARS = 4096
CLOCK_LEEWAY_SECONDS = 10
_jwk_client = None


@dataclass(frozen=True)
class User:
    id: str
    token: str = field(repr=False)   # kept so the database call can run as this user. Never logged.


def jwks_client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        kwargs = {"cache_keys": True, "lifespan": 600}
        if "timeout" in inspect.signature(PyJWKClient.__init__).parameters:
            kwargs["timeout"] = 5
        _jwk_client = PyJWKClient(f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json", **kwargs)
    return _jwk_client


def _unauthorized(message: str = "Invalid or expired token") -> HTTPException:
    return HTTPException(401, message, headers={"WWW-Authenticate": "Bearer"})


def verify_token(token: str) -> dict:
    if len(token) > MAX_TOKEN_CHARS:
        raise _unauthorized()
    try:
        alg = jwt.get_unverified_header(token).get("alg")
        if alg in ASYMMETRIC:
            key = jwks_client().get_signing_key_from_jwt(token).key
        elif alg == "HS256" and settings.SUPABASE_JWT_SECRET:
            key = settings.SUPABASE_JWT_SECRET          # old projects only
        else:
            log.warning("token rejected: unsupported algorithm %r", alg)
            raise _unauthorized()                      # includes alg "none" and anything unexpected
        claims = jwt.decode(
            token, key, algorithms=[alg],              # only the one algorithm we chose above
            audience="authenticated", issuer=f"{settings.SUPABASE_URL}/auth/v1",
            options={"require": ["exp", "sub", "aud", "iss"]},
            leeway=CLOCK_LEEWAY_SECONDS,               # tolerate a few seconds of clock difference
        )
    except HTTPException:
        raise
    except PyJWKClientConnectionError:
        log.error("could not reach the Supabase key endpoint")
        raise HTTPException(503, "Authentication service unavailable")
    except (jwt.PyJWTError, PyJWKClientError) as e:
        # The client only ever sees a plain 401. The reason goes in the server log (these messages never contain the token).
        log.warning("token rejected: %s: %s", type(e).__name__, e)
        raise _unauthorized()
    if claims.get("role") != "authenticated":          # the public anon key is a token too. Reject it.
        log.warning("token rejected: role is %r, not 'authenticated'", claims.get("role"))
        raise _unauthorized()
    try:
        uuid.UUID(str(claims["sub"]))
    except ValueError:
        log.warning("token rejected: subject is not a uuid")
        raise _unauthorized()
    return claims


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise _unauthorized("Missing bearer token")
    claims = verify_token(creds.credentials)
    return User(id=str(claims["sub"]), token=creds.credentials)


def ip_limit(request: Request) -> None:
    """Runs on every request, before login is checked, so floods of bad tokens are throttled too."""
    ip = request.client.host if request.client else "unknown"
    limiter.check(f"ip:{ip}", settings.RATE_LIMIT_IP)


def predict_user(user: User = Depends(get_current_user)) -> User:
    limiter.check(f"predict:{user.id}", settings.RATE_LIMIT_PREDICT)
    return user


def read_user(user: User = Depends(get_current_user)) -> User:
    limiter.check(f"read:{user.id}", settings.RATE_LIMIT_READ)
    return user
