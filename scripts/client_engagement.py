#!/usr/bin/env python3
"""Offline client-engagement preflight for ARTEX. No network or task execution.

Outputs a reviewed task creation payload for the existing POST /api/tasks API.
This validates a claimed authorization record, not the signer's legal authority.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{3,63}$")
DOMAIN_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
MAX_PROOF_BYTES = 5 * 1024 * 1024
REQUIRED = {
    "engagement_id", "client_name", "authorizing_party", "authorization_file",
    "authorized_from", "authorized_until", "scope_hosts",
    "operator_attests_authority", "environment",
}
OPTIONAL = {"excluded_hosts"}


class InvalidEngagement(ValueError):
    """A required preflight condition did not pass."""


def parse_time(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise InvalidEngagement(f"{field} must be an ISO 8601 timestamp with a timezone")
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidEngagement(f"{field} is not ISO 8601") from exc
    if t.tzinfo is None or t.utcoffset() is None:
        raise InvalidEngagement(f"{field} must include a timezone")
    return t.astimezone(timezone.utc)


def normalize_host(value: object) -> str:
    if not isinstance(value, str):
        raise InvalidEngagement("scope hosts must be strings")
    host = value.strip().lower()
    if (not host or len(host) > 253 or any(x in host for x in "/:@?&#*\\\t\n ")
            or host.endswith(".") or host.startswith(".")):
        raise InvalidEngagement(f"invalid exact host: {value!r}")
    if host in {"localhost", "host.docker.internal"} or host.endswith(".localhost"):
        raise InvalidEngagement("localhost is not allowed for client engagements")
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        if re.fullmatch(r"[0-9.]+", host):
            raise InvalidEngagement("invalid IP address")
        labels = host.split(".")
        if len(labels) < 2 or not all(DOMAIN_LABEL.fullmatch(p) for p in labels):
            raise InvalidEngagement(f"invalid DNS host: {value!r}")
        if labels[-1] in {"local", "internal", "test", "invalid"}:
            raise InvalidEngagement("local or non-public domain is not permitted")
    else:
        if not addr.is_global:
            raise InvalidEngagement("non-global IP target is not permitted in client mode")
    return host


def host_list(value: object, field: str, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty) or len(value) > 20:
        raise InvalidEngagement(f"{field} must contain 1-20 exact hosts" if not allow_empty
                                else f"{field} must contain at most 20 exact hosts")
    hosts = [normalize_host(x) for x in value]
    if len(hosts) != len(set(hosts)):
        raise InvalidEngagement(f"{field} has duplicate hosts")
    return sorted(hosts)


def load_and_validate(path: Path, now: datetime | None = None) -> tuple[dict, dict]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InvalidEngagement(f"cannot read manifest: {exc}") from exc
    if not isinstance(data, dict):
        raise InvalidEngagement("manifest must be a JSON object")
    missing, unexpected = REQUIRED - data.keys(), data.keys() - (REQUIRED | OPTIONAL)
    if missing or unexpected:
        raise InvalidEngagement(f"missing fields: {sorted(missing)}; unexpected fields: {sorted(unexpected)}")
    engagement_id = data["engagement_id"]
    if not isinstance(engagement_id, str) or not IDENTIFIER.fullmatch(engagement_id):
        raise InvalidEngagement("engagement_id must be 4-64 letters, numbers, - or _")
    for key in ("client_name", "authorizing_party"):
        if not isinstance(data[key], str) or not 2 <= len(data[key].strip()) <= 120:
            raise InvalidEngagement(f"{key} must be a nonempty name (2-120 characters)")
    if data["operator_attests_authority"] is not True:
        raise InvalidEngagement("operator must explicitly attest to written authorization")
    if data["environment"] not in {"staging", "production"}:
        raise InvalidEngagement("environment must be staging or production")
    start = parse_time(data["authorized_from"], "authorized_from")
    end = parse_time(data["authorized_until"], "authorized_until")
    if not start <= now < end:
        raise InvalidEngagement("engagement authorization is not active at the current time")
    if end <= start or end - start > timedelta(days=90):
        raise InvalidEngagement("authorization window must be positive and at most 90 days")
    hosts = host_list(data["scope_hosts"], "scope_hosts")
    excluded = host_list(data.get("excluded_hosts", []), "excluded_hosts", allow_empty=True)
    if set(hosts) & set(excluded):
        raise InvalidEngagement("a target cannot be both in scope and excluded")
    proof_name = data["authorization_file"]
    if not isinstance(proof_name, str) or not proof_name.strip():
        raise InvalidEngagement("authorization_file must point to a written authorization record")
    proof = (path.resolve().parent / proof_name).resolve()
    if not proof.is_file() or proof.stat().st_size == 0 or proof.stat().st_size > MAX_PROOF_BYTES:
        raise InvalidEngagement("authorization record is missing, empty, or over 5 MiB")
    if proof.suffix.lower() not in {".pdf", ".txt", ".md"}:
        raise InvalidEngagement("authorization record must be PDF, TXT, or Markdown")
    digest = hashlib.sha256(proof.read_bytes()).hexdigest()
    metadata = {
        "engagement_id": engagement_id,
        "client_name": data["client_name"].strip(),
        "authorization_sha256": digest,
        "authorization_file_name": proof.name,
        "authorized_from": start.isoformat(),
        "authorized_until": end.isoformat(),
        "environment": data["environment"],
        "scope_hosts": hosts,
        "excluded_hosts": excluded,
        "operator_attested": True,
        "preflight_checked_at": now.isoformat(),
        "status": "OPERATOR_ATTESTED_NOT_INDEPENDENTLY_VERIFIED",
    }
    return data, metadata


def task_payload(metadata: dict) -> dict:
    hosts = metadata["scope_hosts"]
    engage = metadata["engagement_id"]
    goal = (
        "Perform a low-impact, read-only initial security assessment of only these exact "
        f"authorized hosts: {', '.join(hosts)}. Confirm target ownership and scope before "
        "any active testing. Do not access other hosts, use credential attacks, exploit vulnerabilities, "
        "modify data, establish persistence, exfiltrate content, or cause denial of service. "
        "Stop and request a human decision on uncertainty. Log evidence without sensitive payloads. "
        f"Stop by {metadata['authorized_until']} (UTC)."
    )
    return {
        "description": f"Client engagement {engage} — {metadata['environment']}",
        "goal": goal,
        "target_gate": True,
        "coverage_enabled": True,
        "intercept_rules": [
            {"enabled": True, "action": "allow", "kind": "exact_domain",
             "pattern": host, "note": f"Authorized engagement {engage}; expires {metadata['authorized_until']}"}
            for host in hosts
        ],
    }


def exclusive_json(path: str, data: dict) -> None:
    if path == "-":
        print(json.dumps(data, indent=2))
        return
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Private JSON engagement manifest")
    parser.add_argument("--task-json", metavar="FILE", help="Write reviewed POST /api/tasks JSON, or - for stdout")
    parser.add_argument("--audit-json", metavar="FILE", help="Write authorization hash and metadata, or - for stdout")
    args = parser.parse_args(argv)
    if args.task_json == "-" and args.audit_json == "-":
        parser.error("only one output can be stdout")
    try:
        _, meta = load_and_validate(args.manifest)
        if args.task_json:
            exclusive_json(args.task_json, task_payload(meta))
        if args.audit_json:
            exclusive_json(args.audit_json, meta)
    except (InvalidEngagement, OSError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(f"PASS: {meta['engagement_id']}; {len(meta['scope_hosts'])} exact host(s); "
          "authorization evidence hashed, not independently verified", file=sys.stderr)
    print("NO TASK EXECUTED. Human authorization and runtime enforcement are still required.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
