import base64
import json

import pytest

from app import settings


def _jwt_with_role(role):
    payload = base64.urlsafe_b64encode(json.dumps({"role": role}).encode()).decode().rstrip("=")
    return f"header.{payload}.signature"


def _set_public_config(monkeypatch, **overrides):
    values = {
        "FRAGILEE_ENV": "public",
        "ENV": "prod",
        "STORAGE": "supabase",
        "SUPABASE_URL": "https://abcdefghijklmnopqrst.supabase.co",
        "PUBLIC_SUPABASE_PROJECT_REF": "abcdefghijklmnopqrst",
        "SUPABASE_ANON_KEY": _jwt_with_role("anon"),
        "SUPABASE_JWT_SECRET": "",
        "ALLOWED_ORIGINS": ["https://fragilee.vercel.app"],
    }
    values.update(overrides)
    for name, value in values.items():
        monkeypatch.setattr(settings, name, value)


def test_public_config_accepts_dedicated_supabase_project_and_anon_key(monkeypatch):
    _set_public_config(monkeypatch)

    settings.validate()


def test_public_config_accepts_explicitly_selected_fragilee_project(monkeypatch):
    _set_public_config(
        monkeypatch,
        SUPABASE_URL=f"https://{settings.PRODUCTION_SUPABASE_PROJECT_REF}.supabase.co",
        PUBLIC_SUPABASE_PROJECT_REF=settings.PRODUCTION_SUPABASE_PROJECT_REF,
    )

    settings.validate()


def test_public_config_rejects_project_reference_mismatch(monkeypatch):
    _set_public_config(monkeypatch, SUPABASE_URL=f"https://{settings.PRODUCTION_SUPABASE_PROJECT_REF}.supabase.co")

    with pytest.raises(RuntimeError, match="does not match"):
        settings.validate()


@pytest.mark.parametrize("key", ["sb_secret_not-for-browser", _jwt_with_role("service_role")])
def test_public_config_rejects_secret_and_service_role_keys(monkeypatch, key):
    _set_public_config(monkeypatch, SUPABASE_ANON_KEY=key)

    with pytest.raises(RuntimeError, match="publishable or legacy anon"):
        settings.validate()


def test_public_config_requires_jwks_not_legacy_jwt_secret(monkeypatch):
    _set_public_config(monkeypatch, SUPABASE_JWT_SECRET="must-not-be-configured")

    with pytest.raises(RuntimeError, match="JWKS"):
        settings.validate()


@pytest.mark.parametrize("origins", [[], ["*"] , ["http://fragilee.example"], ["https://fragilee.example/path"]])
def test_public_config_requires_exact_https_origins(monkeypatch, origins):
    _set_public_config(monkeypatch, ALLOWED_ORIGINS=origins)

    with pytest.raises(RuntimeError, match="exact HTTPS"):
        settings.validate()
