#!/usr/bin/env python3
"""One-request OpenRouter free-model tool-call compatibility smoke test.

Default action is offline. --live sends exactly one HTTPS request with synthetic
data. No tools, target scans, or application changes are executed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
TOOL_NAME = "record_lab_result"


def is_free_model(model: str) -> bool:
    return model == "openrouter/free" or (
        model.endswith(":free") and "/" in model and not model.startswith("/")
    )


def make_payload(model: str) -> dict[str, Any]:
    if not is_free_model(model):
        raise ValueError("model must be openrouter/free or an exact :free model variant")
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": "Synthetic API integration test only. No real hosts, people, credentials or customer data."},
            {"role": "user", "content": "Call record_lab_result with test_id 'synthetic-lab-01' and status 'ok'. Do not perform any external action."},
        ],
        "tools": [{
            "type": "function",
            "function": {
                "name": TOOL_NAME,
                "description": "Record an entirely synthetic lab test; no side effects.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "test_id": {"type": "string", "enum": ["synthetic-lab-01"]},
                        "status": {"type": "string", "enum": ["ok"]},
                    },
                    "required": ["test_id", "status"],
                    "additionalProperties": False,
                },
            },
        }],
        "tool_choice": "auto",
        "provider": {"require_parameters": True},
        "max_tokens": 160,
        "temperature": 0,
    }


def validate_answer(data: Any) -> tuple[str, str]:
    if not isinstance(data, dict):
        raise ValueError("response was not a JSON object")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("response did not contain a choice")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise ValueError("response did not contain a message")
    calls = message.get("tool_calls")
    if not isinstance(calls, list) or not calls:
        raise ValueError("model did not generate a function tool call")
    for call in calls:
        func = call.get("function", {}) if isinstance(call, dict) else {}
        if func.get("name") != TOOL_NAME:
            continue
        raw = func.get("arguments")
        try:
            args = json.loads(raw) if isinstance(raw, str) else raw
        except (ValueError, TypeError):
            continue
        if args == {"test_id": "synthetic-lab-01", "status": "ok"}:
            name = data.get("model")
            return (name if isinstance(name, str) else "unreported-model"), "tool-call-valid"
    raise ValueError("model did not return expected function arguments")


def live_probe(model: str, key: str, opener: Any = urllib.request.urlopen) -> tuple[str, str]:
    if not key:
        raise ValueError("OPENROUTER_API_KEY is not configured")
    payload = json.dumps(make_payload(model)).encode("utf-8")
    request = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/thefinalwavesarehere/ARTEX",
            "X-Title": "ARTEX Synthetic Tool Call Smoke",
        },
        method="POST",
    )
    try:
        with opener(request, timeout=30) as response:
            raw = response.read(262145)
    except urllib.error.HTTPError as exc:
        raise ValueError(f"OpenRouter HTTP {exc.code}") from None
    except urllib.error.URLError:
        raise ValueError("network or TLS connection failed") from None
    if len(raw) > 262144:
        raise ValueError("response size exceeded safe bound")
    try:
        return validate_answer(json.loads(raw))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("OpenRouter returned invalid JSON") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="openrouter/free",
                        help="openrouter/free or a provider/model:free slug")
    parser.add_argument("--live", action="store_true",
                        help="Send one synthetic HTTPS request to OpenRouter")
    args = parser.parse_args(argv)
    try:
        make_payload(args.model)
        if not args.live:
            print("PASS: offline payload validated; NO NETWORK REQUEST SENT")
            print(f"Model: {args.model}; provider: OpenRouter; mode: synthetic tool-call smoke")
            print("Next: set OPENROUTER_API_KEY privately, then rerun with --live")
            return 0
        selected, result = live_probe(args.model, os.environ.get("OPENROUTER_API_KEY", ""))
        print(f"PASS: {result}; requested={args.model}; responded={selected}; requests=1")
        print("NOT VERIFIED: ARTEX agent integration or scan containment")
        return 0
    except ValueError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
