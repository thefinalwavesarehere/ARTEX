"""OpenRouter free-model smoke tests. Never open a network connection."""
import importlib.util
import json
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("openrouter_smoke", Path(__file__).with_name("openrouter_smoke.py"))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class FakeReply:
    def __init__(self, body):
        self.body = json.dumps(body).encode()
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self, limit):
        return self.body[:limit]


def mock_body(args='{"test_id":"synthetic-lab-01","status":"ok"}'):
    return {"model": "vendor/sample:free", "choices": [{"message": {"tool_calls": [
        {"type": "function", "function": {"name": "record_lab_result", "arguments": args}}
    ]}}]}


class OpenRouterSmokeTests(unittest.TestCase):
    def test_auto_free(self):
        self.assertEqual(probe.make_payload("openrouter/free")["model"], "openrouter/free")
    def test_explicit_free(self):
        self.assertEqual(probe.make_payload("vendor/model:free")["model"], "vendor/model:free")
    def test_paid_rejected(self):
        with self.assertRaises(ValueError):
            probe.make_payload("vendor/paid-model")
    def test_invalid_slug(self):
        with self.assertRaises(ValueError):
            probe.make_payload("free")
    def test_tools_required(self):
        p = probe.make_payload("openrouter/free")
        self.assertTrue(p["provider"]["require_parameters"])
        self.assertEqual(p["tools"][0]["function"]["name"], "record_lab_result")
    def test_valid_response(self):
        self.assertEqual(probe.validate_answer(mock_body()), ("vendor/sample:free", "tool-call-valid"))
    def test_missing_call(self):
        with self.assertRaises(ValueError):
            probe.validate_answer({"choices": [{"message": {"content": "ok"}}]})
    def test_wrong_arguments(self):
        with self.assertRaises(ValueError):
            probe.validate_answer(mock_body('{"test_id":"wrong","status":"ok"}'))
    def test_invalid_arguments(self):
        with self.assertRaises(ValueError):
            probe.validate_answer(mock_body("not-json"))
    def test_injected_mock_one_request(self):
        requests = []
        def opener(req, timeout):
            requests.append((req.full_url, timeout, json.loads(req.data)))
            return FakeReply(mock_body())
        out = probe.live_probe("openrouter/free", "dummy-secret", opener=opener)
        self.assertEqual(out[1], "tool-call-valid")
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0][0], probe.ENDPOINT)
        self.assertEqual(requests[0][2]["model"], "openrouter/free")
    def test_missing_key(self):
        with self.assertRaises(ValueError):
            probe.live_probe("openrouter/free", "", opener=lambda *_: None)
    def test_default_offline(self):
        self.assertEqual(probe.main([]), 0)


if __name__ == "__main__":
    unittest.main()
