# Client pentest service — release backlog

**Date:** 2026-11-20  
**Status:** blocked for hosted commercial launch  
**Tracking:** GitHub Issues are disabled in this fork (create attempts returned HTTP 410). Track changes in this file until Issues are enabled.  
**Implementation branch:** feat/client-pentest-pilot-20261120

## P0 — Runtime authorization and scope enforcement

**Problem:** The existing target gate is optional; the historical rules-of-engagement mechanism was removed.

- Require a reviewed engagement record, exact approved targets, an operator identity, and an active UTC window before any client-mode execution.
- Apply the boundary to task creation/updates, child tasks, chat sessions, shell/custom tools, plugins/MCP, replay, proxies and redirects.
- Reject scope widening unless newly authorized. Stop tasks immediately when permission is revoked or expires.
- Make runtime state and outcome auditable.

**Acceptance:** Isolated integration tests prove no task/tool/network action on missing, expired or revoked authorization; all child and replay paths remain in scope.

## P0 — Network containment and emergency stop

**Problem:** Application gates and noise controls are not a firewall; shell-based commands may bypass the host request pacer.

- Provide per-engagement deny-by-default egress proxy/firewall rules for allowed host, port and pinned address.
- Protect against DNS rebinding, redirect escapes, proxy bypasses, IPv6 and access to internal/cloud-metadata networks.
- Enforce request/time/connection budgets independent of agent prompts.
- A stop action must revoke further egress and terminate running work.

**Acceptance:** Lab tests prove all out-of-scope attempts are denied across every supported tool, including shell, proxy and custom tools. Stop succeeds even with active requests.

## P0 — Privacy and isolation for each client

**Problem:** Shared-instance multi-tenancy is unverified, and captured evidence may contain credentials or personal information.

- Pilot: provision separate ARTEX instance, PostgreSQL, keys, storage and network controls per client.
- Validate authorization for all APIs and exports before considering shared tenancy.
- Redact cookies/secrets and limit access to evidence; use secure delivery and deletion audit.
- Test backup restore and secure closeout.

**Acceptance:** Two-client data isolation tests pass; sensitive values do not appear in exported reports; access control and retention audit pass.

## P1 — End-to-end safe pilot

- Build an isolated, owned vulnerable demonstration app with no external test targets.
- Exercise contract intake, offline preflight, API guard, controlled tests, evidence, verification, report and authorized retest.
- Test stop/revocation, redirects, blocked hosts, expired permission and false positives.
- Review dependency and supply-chain security and verify Docker build reproducibility.
- Capture go, web, Python, and integration CI results and approved deployment configuration.

**Acceptance:** Repeatable offline/lab pilot produces a fact-checked report with no unexpected network traffic.

## P1 — Developer-facing value and service integration

- Add opt-in source-code scanning (SAST), secret detection, dependency and IaC checks for repositories the customer authorizes.
- Build a remediation proposal workflow: developer-ready fixes and retest, but no unauthorized merges or production deployments.
- Add project intake, secured result delivery, coverage metadata, operator sign-off, and optional follow-up assessments.
- Distinguish confirmed, suspected, untested, fixed, and cannot-confirm findings. Do not imply Aikido feature parity.

**Acceptance:** Owned demo repository yields triaged source findings and an unmerged remediation proposal; report provides exact acceptance conditions and exclusions.

## P1 — Legal/commercial review

- Confirm AGPL-3.0 attribution and network-use corresponding-source obligations for modified hosted use.
- Review customer consent/ROE, privacy/data processing, service terms, liability, retention and incident handling.
- Verify marketing claims against live evidence. No security certification or guarantee of finding all vulnerabilities.

**Acceptance:** Approved service agreement, notice/source workflow, data-processing controls, and validated marketing copy.

## Release decision

- **Offline preflight:** implemented, local unit tests passed; CI must confirm.
- **Controlled live testing:** BLOCKED pending P0 runtime, authorization, egress and lab validation.
- **Public multi-client SaaS:** BLOCKED pending all P0 and client isolation/security reviews.
- **Aikido-level continuous product:** NOT IMPLEMENTED; independent service roadmap item.
