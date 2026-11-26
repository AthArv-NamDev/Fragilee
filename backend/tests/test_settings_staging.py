import pytest

from app import settings


def test_local_settings_report_the_local_supabase_project_id(monkeypatch):
    monkeypatch.setattr(settings, "FRAGILEE_ENV", "local")
    monkeypatch.setattr(settings, "SUPABASE_URL", "http://127.0.0.1:54321")

    assert settings.supabase_project_ref() == "fragilee-local"


def test_staging_settings_refuse_known_production_project(monkeypatch):
    monkeypatch.setattr(settings, "FRAGILEE_ENV", "staging")
    monkeypatch.setattr(settings, "ENV", "dev")
    monkeypatch.setattr(settings, "STORAGE", "supabase")
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://ayrxcjlonouqluysnhlg.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_ANON_KEY", "public-key-not-logged")
    with pytest.raises(RuntimeError, match="known Production"):
        settings.validate()


def test_staging_settings_require_persistent_supabase_storage(monkeypatch):
    monkeypatch.setattr(settings, "FRAGILEE_ENV", "staging")
    monkeypatch.setattr(settings, "ENV", "dev")
    monkeypatch.setattr(settings, "STORAGE", "memory")
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://stageproject12345678.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_ANON_KEY", "staging-public-key")
    with pytest.raises(RuntimeError, match="STORAGE=supabase"):
        settings.validate()
