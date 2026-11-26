import base64
import hashlib
import hmac
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from local_supabase import clean_runtime_env
from local_supabase_config import LocalSupabaseConfigError, load_local_config


def _anon_jwt() -> str:
    secret = "local-test-jwt-secret-that-is-long-enough"
    def encode(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")
    signing_input = f"{encode({'alg': 'HS256', 'typ': 'JWT'})}.{encode({'role': 'anon'})}"
    signature = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{signing_input}.{encoded_signature}"


def env_text(key: str = "sb_publishable_localtestkey123456"):
    frontend = f"""FRAGILEE_ENV=local
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY={key}
NEXT_PUBLIC_API_URL=http://127.0.0.1:8001
"""
    backend = f"""FRAGILEE_ENV=local
ENV=dev
STORAGE=supabase
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY={key}
SUPABASE_JWT_SECRET=local-test-jwt-secret-that-is-long-enough
ALLOWED_ORIGINS=http://localhost:3001
"""
    return frontend, backend


class LocalSupabaseConfigTests(unittest.TestCase):
    def validate(self, frontend: str, backend: str):
        with tempfile.TemporaryDirectory() as tmp:
            frontend_path = Path(tmp) / "frontend.env"
            backend_path = Path(tmp) / "backend.env"
            frontend_path.write_text(frontend)
            backend_path.write_text(backend)
            return load_local_config(frontend_path, backend_path)

    def test_matching_local_configuration_is_accepted(self):
        front, back = env_text()
        frontend, backend = self.validate(front, back)
        self.assertEqual(frontend["FRAGILEE_ENV"], "local")
        self.assertEqual(backend["SUPABASE_URL"], "http://127.0.0.1:54321")

    def test_legacy_local_anon_jwt_key_is_accepted(self):
        front, back = env_text(_anon_jwt())
        self.validate(front, back)

    def test_invalid_legacy_anon_jwt_signature_is_rejected(self):
        token = _anon_jwt()
        head, payload, signature = token.split(".")
        signature = ("A" if signature[0] != "A" else "B") + signature[1:]
        front, back = env_text(f"{head}.{payload}.{signature}")
        with self.assertRaisesRegex(LocalSupabaseConfigError, "signature does not match"):
            self.validate(front, back)

    def test_missing_credentials_are_rejected(self):
        front, back = env_text()
        with self.assertRaisesRegex(LocalSupabaseConfigError, "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"):
            self.validate(front.replace("sb_publishable_localtestkey", ""), back)

    def test_production_and_other_hosted_urls_are_rejected(self):
        front, back = env_text()
        with self.assertRaisesRegex(LocalSupabaseConfigError, "hosted URLs are refused"):
            self.validate(front.replace("http://127.0.0.1:54321", "https://ayrxcjlonouqluysnhlg.supabase.co"), back)
        with self.assertRaisesRegex(LocalSupabaseConfigError, "hosted URLs are refused"):
            self.validate(front.replace("http://127.0.0.1:54321", "https://other-project.supabase.co"), back)

    def test_mismatched_frontend_and_backend_urls_are_rejected(self):
        front, back = env_text()
        with self.assertRaisesRegex(LocalSupabaseConfigError, "must be exactly"):
            self.validate(front, back.replace("http://127.0.0.1:54321", "http://127.0.0.1:54322"))

    def test_invalid_or_service_role_keys_are_rejected(self):
        front, back = env_text("not-a-key")
        with self.assertRaisesRegex(LocalSupabaseConfigError, "must be a local publishable key"):
            self.validate(front, back)
        front, back = env_text("sb_secret_localtestkey")
        with self.assertRaisesRegex(LocalSupabaseConfigError, "never a secret key"):
            self.validate(front, back)
        front, back = env_text("sb_publishable_too_short")
        with self.assertRaisesRegex(LocalSupabaseConfigError, "not a valid publishable key"):
            self.validate(front, back)
        front, back = env_text()
        with self.assertRaisesRegex(LocalSupabaseConfigError, "Service-role and secret keys"):
            self.validate(front, back + "SUPABASE_SERVICE_ROLE_KEY=must-not-be-present\n")

    def test_frontend_and_backend_keys_must_match(self):
        front, back = env_text()
        with self.assertRaisesRegex(LocalSupabaseConfigError, "same local public key"):
            self.validate(front, back.replace("sb_publishable_localtestkey123456", "sb_publishable_otherkey123456789012345678"))

    def test_missing_local_mode_and_production_env_are_rejected(self):
        front, back = env_text()
        with self.assertRaisesRegex(LocalSupabaseConfigError, "FRAGILEE_ENV=local"):
            self.validate(front.replace("FRAGILEE_ENV=local", "FRAGILEE_ENV=staging"), back)
        with self.assertRaisesRegex(LocalSupabaseConfigError, "ENV=prod"):
            self.validate(front, back.replace("ENV=dev", "ENV=prod"))

    def test_launch_environment_does_not_inherit_hosted_project_values(self):
        front, _ = env_text()
        frontend, _ = self.validate(front, env_text()[1])
        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://hosted-project.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "must-not-leak",
            "NEXT_PUBLIC_SUPABASE_URL": "https://hosted-project.supabase.co",
        }, clear=True):
            runtime = clean_runtime_env(frontend, frontend=True)
        self.assertEqual(runtime["NEXT_PUBLIC_SUPABASE_URL"], "http://127.0.0.1:54321")
        self.assertEqual(runtime["FRAGILEE_ENV"], "local")
        self.assertNotIn("SUPABASE_URL", runtime)
        self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY", runtime)


if __name__ == "__main__":
    unittest.main()
