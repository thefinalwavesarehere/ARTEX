# ARTEX client pilot — start here

This fork includes an **offline authorization preflight**, a scoped task-draft generator, and client engagement templates.

1. For free-model setup, read the [OpenRouter lab guide](docs/OPENROUTER_LAB.md). Its smoke test is offline by default and cannot run a pentest.
2. Read [operator runbook](docs/CLIENT_PENTEST_PILOT.md).
3. Review [authorization template](docs/templates/authorization_letter.md).
4. Copy [example manifest](docs/templates/engagement.example.json) into private storage, then attach a real written authorization record.
6. Run `python3 scripts/client_engagement.py --help` locally. The script only validates and creates files; it does not launch ARTEX or touch a target.
5. Run the offline deployment check on your private .env file: python3 scripts/client_deployment_check.py .env. This does not start containers.
7. Use the [client report template](docs/templates/client_report.md) after human validation.

**Not production-ready as a hosted pentest service.** Do not operate unattended testing of third-party systems. Use separate instances and independent egress enforcement until the release blockers are closed.

The upstream framework uses AGPL-3.0; preserve required license notices and assess obligations before commercial hosting.
