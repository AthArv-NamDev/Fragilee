import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from staging_config import StagingConfigError, load_staging_config, verify_remote_public_key


def contents(front_ref="stageproject12345678", back_ref=None, front_ref_override=None):
    back_ref = back_ref or front_ref
    front_ref = front_ref_override or front_ref
    frontend = f"""FRAGILEE_ENV=staging
NEXT_PUBLIC_SUPABASE_URL=https://{front_ref}.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_staging_test
NEXT_PUBLIC_API_URL=http://127.0.0.1:8001
"""
    backend = f"""FRAGILEE_ENV=staging
ENV=dev
STORAGE=supabase
SUPABASE_URL=https://{back_ref}.supabase.co
SUPABASE_ANON_KEY=sb_publishable_staging_test
ALLOWED_ORIGINS=http://localhost:3001
"""
    return frontend, backend


class StagingConfigTests(unittest.TestCase):
    def validate(self, frontend_text, backend_text):
        with tempfile.TemporaryDirectory() as tmp:
            front = Path(tmp) / "frontend.staging.env"
            back = Path(tmp) / "backend.staging.env"
            front.write_text(frontend_text)
            back.write_text(backend_text)
            return load_staging_config(front, back)

    def test_matching_nonproduction_project_is_accepted(self):
        front, back = contents()
        self.assertEqual(self.validate(front, back)[2], "stageproject12345678")

    def test_production_project_is_rejected(self):
        front, back = contents(front_ref="ayrxcjlonouqluysnhlg")
        with self.assertRaisesRegex(StagingConfigError, "known Production"):
            self.validate(front, back)

    def test_mismatched_frontend_and_backend_projects_are_rejected(self):
        front, back = contents(back_ref="otherstage1234567890")
        with self.assertRaisesRegex(StagingConfigError, "do not match"):
            self.validate(front, back)

    def test_missing_values_and_service_role_are_rejected(self):
        front, back = contents()
        with self.assertRaisesRegex(StagingConfigError, "Set NEXT_PUBLIC_SUPABASE"):
            self.validate(front.replace("sb_publishable_staging_test", "your-publishable-key"), back)
        with self.assertRaisesRegex(StagingConfigError, "service-role"):
            self.validate(front, back + "SUPABASE_SERVICE_ROLE_KEY=must-not-be-used\n")

    def test_different_public_keys_are_rejected(self):
        front, back = contents()
        with self.assertRaisesRegex(StagingConfigError, "same staging public key"):
            self.validate(front, back.replace("sb_publishable_staging_test", "another-key"))

    @patch("staging_config.urlopen")
    def test_read_only_key_probe_targets_the_staging_project(self, open_url):
        front, back = contents()
        frontend, _, project_ref = self.validate(front, back)
        response = open_url.return_value.__enter__.return_value
        response.status = 200
        response.read.return_value = b"{"
        verify_remote_public_key(frontend, project_ref)
        request = open_url.call_args.args[0]
        self.assertIn(project_ref, request.full_url)
        self.assertEqual(request.method, "GET")

    @patch("staging_config.urlopen")
    def test_production_key_probe_is_refused_before_network(self, open_url):
        front, back = contents(front_ref="ayrxcjlonouqluysnhlg")
        with self.assertRaisesRegex(StagingConfigError, "known Production"):
            self.validate(front, back)
        open_url.assert_not_called()


if __name__ == "__main__":
    unittest.main()
