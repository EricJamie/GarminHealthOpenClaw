# Changelog

## 0.1.0

Initial release candidate for the local Garmin + OpenClaw workflow.

### Added

- vendored Garmin authentication module
- token-data-first authentication flow
- token refresh and auth validation scripts
- live Garmin fetch validation script
- question-driven Garmin query CLI
- structured `query result` output with:
  - `meta`
  - `data`
  - `highlights`
  - `guidance`
  - `missing`
- support for 5 question types:
  - `sleep_recovery`
  - `training_state`
  - `activity_history`
  - `performance_prediction`
  - `composite_health`
- coaching-style evidence and recommendation layer
- internal OpenClaw skill
- public OpenClaw skill template
- product, architecture, routing, CLI, deployment, and publishing docs

### Verified

- auth boundary tests
- query CLI tests
- live validation against a real Garmin account during development

### Known Scope Limits

- optimized for local single-user usage
- no public installer yet
- no long-horizon training plan generation yet
- no strict token-only mode yet
