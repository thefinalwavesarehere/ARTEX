#!/usr/bin/env python3
"""Offline sanity checks for a dedicated ARTEX client-pilot .env file.

No network access, no Docker command, and no secret values in output.
These are prerequisites, not a substitute for runtime or network isolation.
"""
from __future__ import annotations
import argparse
import ipaddress
import sys
from pathlib import Path

REQUIRED_BUDGETS = ("ARTEX_TASK_BUDGET_TOKENS", "ARTEX_TASK_BUDGET_TURNS", "ARTEX_INTENT_BUDGET_TOKENS", "ARTEX_INTENT_BUDGET_TURNS")


def parse_env(source: str) -> dict[str, str]:
    values = {}
    for n, original in enumerate(source.splitlines(), 1):
        line = original.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"line {n}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or not key.replace("_", "").isalnum():
            raise ValueError(f"line {n}: invalid key")
        if key in values:
            raise ValueError(f"line {n}: duplicate key {key}")
        value = value.strip()
        if value.startswith(('"', "'")) and value[-1:] == value[:1]:
            value = value[1:-1]
        values[key] = value
    return values


def review(values: dict[str, str]) -> list[str]:
    failures = []
    addr = values.get("ARTEX_BIND_ADDR", "")
    try:
        bind_ok = ipaddress.ip_address(addr).is_loopback
    except ValueError:
        bind_ok = False
    if not bind_ok:
        failures.append("ARTEX_BIND_ADDR must be a loopback IP")
    password = values.get("POSTGRES_PASSWORD", "")
    if len(password) < 24 or password.lower() in {"change-me-please", "testpass", "password"}:
        failures.append("POSTGRES_PASSWORD must be a non-default value of at least 24 characters")
    if values.get("ARTEX_NOISE_PROFILE") != "quiet":
        failures.append("ARTEX_NOISE_PROFILE must be quiet")
    if values.get("ARTEX_UNTRUSTED_BOUNDARY", "").lower() in {"0", "false", "off", "no"}:
        failures.append("ARTEX_UNTRUSTED_BOUNDARY may not be disabled")
    if values.get("ARTEX_LLM_PRIVATE_ENDPOINTS", "").strip():
        failures.append("ARTEX_LLM_PRIVATE_ENDPOINTS requires separate documented review")
    for key in REQUIRED_BUDGETS:
        try:
            val = int(values.get(key, ""))
        except ValueError:
            val = 0
        if not 0 < val <= 10000000:
            failures.append(f"{key} must be set to a positive finite limit")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("env_file", type=Path)
    args = parser.parse_args(argv)
    try:
        values = parse_env(args.env_file.read_text(encoding="utf-8"))
        failures = review(values)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"BLOCKED: cannot validate deployment configuration: {exc}", file=sys.stderr)
        return 2
    for item in failures:
        print(f"BLOCKED: {item}", file=sys.stderr)
    if failures:
        return 2
    print("PASS: offline deployment defaults inspected. Secrets not printed.")
    print("NOT VERIFIED: running containers, database, consent, egress, TLS, user permissions and network isolation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
