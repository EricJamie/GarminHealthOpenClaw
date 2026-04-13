# GarminHealthOpenClaw

GarminHealthOpenClaw is a local Garmin data assistant project built for OpenClaw.

It uses a vendored Garmin authentication flow, fetches Garmin data through local Python CLI commands, and returns structured JSON that OpenClaw can turn into evidence-based coaching-style answers.

## Version

Current planned release: `0.1.0`

## What `0.1.0` Includes

- Vendored Garmin authentication foundation
- `GARMIN_TOKEN_DATA`-first auth flow
- Local CLI query entrypoint
- 5 supported question types:
  - `sleep_recovery`
  - `training_state`
  - `activity_history`
  - `performance_prediction`
  - `composite_health`
- OpenClaw skill integration
- Evidence-based coaching-style answer structure

## Project Shape

This project is organized around:

1. Garmin auth
2. Question-driven query planning
3. Structured query-result building
4. OpenClaw skill integration

## Main CLI

The main local entrypoint is:

```bash
python3 scripts/garmin_query.py <question_type> [options]
```

Examples:

```bash
python3 scripts/garmin_query.py sleep_recovery --pretty
python3 scripts/garmin_query.py training_state --pretty
python3 scripts/garmin_query.py activity_history --days 7 --pretty
python3 scripts/garmin_query.py performance_prediction --pretty
python3 scripts/garmin_query.py composite_health --days 7 --pretty
```

## Environment

Runtime prefers:

1. `GARMIN_TOKEN_DATA`
2. `GARMIN_EMAIL` + `GARMIN_PASSWORD` only as bootstrap or fallback

Example:

```env
GARMIN_TOKEN_DATA='{"di_token":"...","di_refresh_token":"...","di_client_id":"..."}'
GARMIN_EMAIL='your_email@example.com'
GARMIN_PASSWORD='your_password'
```

## OpenClaw Integration

This repository contains an OpenClaw skill template in:

- `openclaw-skill-garmin-question-assistant/SKILL.md`

Update `<GARMIN_PROJECT_ROOT>` in that file to your local project path before installing it into your OpenClaw skills directory.

## Tests

Run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Notes

- This project is designed for conservative Garmin access patterns.
- The login delay and vendored auth guardrails are intentional.
- `0.1.0` is aimed at single-user local usage first.
