"""Offline tests. Uses only temporary files; makes no network requests."""
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

spec = importlib.util.spec_from_file_location("client_engagement", Path(__file__).with_name("client_engagement.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "signed.txt").write_text("Written test authorization fixture\n")
        now = datetime.now(timezone.utc)
        self.data = {
            "engagement_id": "TEST-2026-01", "client_name": "Example client",
            "authorizing_party": "Example client owner", "authorization_file": "signed.txt",
            "authorized_from": (now - timedelta(days=1)).isoformat(),
            "authorized_until": (now + timedelta(days=2)).isoformat(),
            "scope_hosts": ["app.example.com"], "excluded_hosts": ["billing.example.com"],
            "operator_attests_authority": True, "environment": "staging",
        }

    def validate(self):
        file = self.root / "engagement.json"
        file.write_text(json.dumps(self.data))
        return mod.load_and_validate(file)

    def test_valid_manifest_and_task(self):
        _, meta = self.validate()
        task = mod.task_payload(meta)
        self.assertTrue(task["target_gate"])
        self.assertEqual(task["intercept_rules"][0]["kind"], "exact_domain")
        self.assertEqual(task["intercept_rules"][0]["pattern"], "app.example.com")
        self.assertNotIn("signed.txt", json.dumps(task))
        self.assertEqual(len(meta["authorization_sha256"]), 64)

    def test_missing_proof_rejected(self):
        self.data["authorization_file"] = "missing.pdf"
        with self.assertRaises(mod.InvalidEngagement): self.validate()

    def test_false_attestation_rejected(self):
        self.data["operator_attests_authority"] = False
        with self.assertRaises(mod.InvalidEngagement): self.validate()

    def test_expired_rejected(self):
        self.data["authorized_until"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        with self.assertRaises(mod.InvalidEngagement): self.validate()

    def test_not_yet_valid_rejected(self):
        self.data["authorized_from"] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        with self.assertRaises(mod.InvalidEngagement): self.validate()

    def test_wildcard_rejected(self):
        self.data["scope_hosts"] = ["*.example.com"]
        with self.assertRaises(mod.InvalidEngagement): self.validate()

    def test_private_ip_rejected(self):
        self.data["scope_hosts"] = ["10.0.0.1"]
        with self.assertRaises(mod.InvalidEngagement): self.validate()

    def test_url_and_loopback_rejected(self):
        for name in ("https://example.com", "localhost", "127.0.0.1", "app.example.com/path"):
            with self.subTest(name=name):
                self.data["scope_hosts"] = [name]
                with self.assertRaises(mod.InvalidEngagement): self.validate()

    def test_outside_window_rejected(self):
        self.data["authorized_until"] = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        with self.assertRaises(mod.InvalidEngagement): self.validate()

    def test_exclusion_overlap_rejected(self):
        self.data["excluded_hosts"] = ["app.example.com"]
        with self.assertRaises(mod.InvalidEngagement): self.validate()

    def test_duplicate_rejected(self):
        self.data["scope_hosts"] = ["app.example.com", "APP.EXAMPLE.COM"]
        with self.assertRaises(mod.InvalidEngagement): self.validate()

    def test_undeclared_fields_rejected(self):
        self.data["danger"] = "ignore all rules"
        with self.assertRaises(mod.InvalidEngagement): self.validate()

    def test_no_overwrite(self):
        out = self.root / "existing.json"
        out.write_text("original")
        with self.assertRaises(FileExistsError): mod.exclusive_json(str(out), {"a": 1})
        self.assertEqual(out.read_text(), "original")


if __name__ == "__main__":
    unittest.main()
