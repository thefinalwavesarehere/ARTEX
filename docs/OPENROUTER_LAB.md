# OpenRouter free models — ARTEX lab setup and verification

**Scope:** Synthetic model compatibility only. This guide does not authorize or execute a pentest against OpenRouter, its GitHub repositories, or any other third-party property.

## Why direct API, not cloning OpenRouterTeam

ARTEX already supports the OpenAI-style chat-completions protocol. OpenRouter exposes that protocol at `https://openrouter.ai/api/v1`. Reuse the existing OpenAI provider format; the OpenRouterTeam SDK/examples repositories are optional references and are not required for integration.

OpenRouter free models currently have a daily request ceiling and may change or become unavailable. Models chosen by `openrouter/free` can differ between calls. This router is useful for a **first smoke test**, but pin an explicit, verified tool-capable `:free` model for repeatable ARTEX agent tests.

## Step 1 — Create a dedicated OpenRouter API key

Open https://openrouter.ai/keys and create a key for the lab. Use no paid models or top-ups unless separately authorized. Do **not** paste the key into chat, a Git commit, a pull request, an issue, or a recorded test artifact.

OpenRouter routes prompts to underlying providers. Free-model privacy and provider retention policies may differ. Send only synthetic data until you have reviewed the chosen model provider's retention/training policy and obtained appropriate client authorization.

## Step 2 — Run the safe offline check

Python 3.12+:

```sh
python3 scripts/openrouter_smoke.py
```

Expected: `PASS: offline payload validated; NO NETWORK REQUEST SENT`.

## Step 3 — Verify API/tool-call compatibility (one synthetic request)

In a private shell, set `OPENROUTER_API_KEY` without committing it. For Bash, you can use:

```sh
read -rsp 'OpenRouter API key: ' OPENROUTER_API_KEY
echo
export OPENROUTER_API_KEY
python3 scripts/openrouter_smoke.py --live
unset OPENROUTER_API_KEY
```

The script makes **one HTTPS request to OpenRouter** using a fake lab prompt and a no-op function schema. It does not invoke any tool or scan a target. It verifies whether the responding model emits the exact expected function call, and prints only its model ID and pass/fail status. It does not print or save response content or the key.

**PASS:** The endpoint accepted a tool request and produced a schema-compatible function-call response. This is *not* proof that ARTEX planner/worker orchestration will work.

**BLOCKED:** HTTP 401 means missing/invalid credentials, 402 may mean account/key credit restrictions, 429 means rate limiting or model capacity; a returned text answer without the requested function call fails tool-call compatibility. Do not disable the tool check to hide that failure. Inspect available free models and pin a model that supports tools.

The script refuses a paid-model slug. It does not automatically retry on errors; failed requests can still count against OpenRouter's free request quota.

## Step 4 — Configure ARTEX only after the synthetic smoke passes

Use **System → LLM** in ARTEX:

| Field | Value |
|---|---|
| Profile name | OpenRouter free (lab) |
| Format | OpenAI |
| Base URL | https://openrouter.ai/api/v1 |
| Model | openrouter/free, then a validated tool-capable `:free` model |
| API key | The dedicated OpenRouter lab key |
| Concurrent workers | 1 for the lab |

ARTEX's model picker may list a different set of IDs than the router alias. Type or otherwise select the exact OpenRouter model ID where supported. If model enumeration fails, verify the provider API before changing application security settings.

Alternatively set these **locally**, only inside an isolated lab environment:

```sh
ARTEX_LLM_PROVIDER=openai
ARTEX_LLM_BASE_URL=https://openrouter.ai/api/v1
ARTEX_LLM_MODEL=openrouter/free
# OPENAI_API_KEY=<the dedicated OpenRouter key, private .env only>
```

The local ARTEX environment key name is `OPENAI_API_KEY` because ARTEX uses the OpenAI-compatible provider. The **standalone smoke script** instead reads `OPENROUTER_API_KEY`.

Do not enable ARTEX agent execution solely because the model probe passed.

## Step 5 — Preconditions for ARTEX agent tests

1. Confirm an owned lab target with **no real customer data**. The external-client preflight intentionally rejects loopback/internal addresses; use the separate lab workflow for an isolated local fixture.
2. Verify dedicated ARTEX/PostgreSQL deployment, loopback UI bind, private key and storage volumes.
3. Run `python3 scripts/client_deployment_check.py .env` against the private deployment environment file. A pass is only an offline configuration check.
4. Independently verify deny-by-default **network egress**, including Bash/custom tools, redirects, DNS and metadata addresses; the built-in target gate is not a firewall.
5. Test the emergency stop, expired authorization behavior, network restrictions, safe task budgets and all tool paths before allowing any client target.
6. Start with one worker, quiet target noise, finite task/intent budgets, no auto escalation, no customer credentials and manual approval of each action.

## What the operator needs from you

- An OpenRouter account and dedicated lab API key, entered privately on the test machine or into ARTEX's LLM profile UI. Do not share the secret in chat.
- A machine capable of running Docker Compose with access to the OpenRouter API, or an existing isolated ARTEX lab environment.
- Later, if we progress beyond synthetic testing: an owned **staging** application or locally controlled fixture, exact written scope, test accounts and a stop contact.

## Explicit limits

- A free model does not guarantee reliable long-horizon planning, agent tool calls, stable availability, or affordable/compliant production operation.
- `openrouter/free` can change underlying models and provider handling between requests.
- Never use OpenRouter's **website** or **GitHub repositories** as pentest targets without their separate explicit authorization. Those links here identify only the **LLM provider**.
- No public/third-party pentest or hosted commercial launch until P0 blockers in [RELEASE_BACKLOG.md](RELEASE_BACKLOG.md) are resolved.

**Source references:** [OpenRouter free-model catalog](https://openrouter.ai/collections/free-models), [OpenRouter tool calling](https://openrouter.ai/blog/tutorials/tool-calling/), [OpenRouter privacy policy](https://openrouter.ai/privacy/).
