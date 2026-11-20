# ARTEX client pilot — start here

This fork includes an **offline authorization preflight**, a scoped task-draft generator, and client engagement templates.

1. Read [operator runbook](docs/CLIENT_PENTEST_PILOT.md).
2. Review [authorization template](docs/templates/authorization_letter.md).
3. Copy [example manifest](docs/templates/engagement.example.json) into private storage, then attach a real written authorization record.
4. Run `python3 scripts/client_engagement.py --help` locally. The script only validates and creates files; it does not launch ARTEX or touch a target.
5. Use the [client report template](docs/templates/client_report.md) after human validation.

**Not production-ready as a hosted pentest service.** Do not operate unattended testing of third-party systems. Use separate instances and independent egress enforcement until the release blockers are closed.

The upstream framework uses AGPL-3.0; preserve required license notices and assess obligations before commercial hosting.
