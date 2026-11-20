"""Offline deployment checker tests (no network or subprocess)."""
import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location("client_deployment_check",Path(__file__).with_name("client_deployment_check.py"))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class DeploymentChecks(unittest.TestCase):
    def setUp(self):
        self.config={
            "ARTEX_BIND_ADDR":"127.0.0.1",
            "POSTGRES_PASSWORD":"this-is-a-test-password-long-enough-32",
            "ARTEX_NOISE_PROFILE":"quiet",
            "ARTEX_TASK_BUDGET_TOKENS":"100000",
            "ARTEX_TASK_BUDGET_TURNS":"20",
            "ARTEX_INTENT_BUDGET_TOKENS":"50000",
            "ARTEX_INTENT_BUDGET_TURNS":"5",
        }
    def test_pass(self): self.assertEqual(mod.review(self.config),[])
    def test_bad_bind(self):
        self.config["ARTEX_BIND_ADDR"]="0.0.0.0"
        self.assertTrue(mod.review(self.config))
    def test_default_password(self):
        self.config["POSTGRES_PASSWORD"]="change-me-please"
        self.assertTrue(mod.review(self.config))
    def test_unbounded(self):
        del self.config["ARTEX_TASK_BUDGET_TURNS"]
        self.assertTrue(mod.review(self.config))
    def test_noise_off(self):
        self.config["ARTEX_NOISE_PROFILE"]="off"
        self.assertTrue(mod.review(self.config))
    def test_private_models(self):
        self.config["ARTEX_LLM_PRIVATE_ENDPOINTS"]="127.0.0.1:11434"
        self.assertTrue(mod.review(self.config))
    def test_no_trust_boundary(self):
        self.config["ARTEX_UNTRUSTED_BOUNDARY"]="0"
        self.assertTrue(mod.review(self.config))
    def test_duplicate_key(self):
        with self.assertRaises(ValueError): mod.parse_env("A=1\nA=2")
    def test_secret_not_in_failure(self):
        self.config["POSTGRES_PASSWORD"]="hunter2"
        self.assertNotIn("hunter2", str(mod.review(self.config)))

if __name__=="__main__": unittest.main()
