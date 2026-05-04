# Phase B Implementation

Phase B goal is to make `MCS` stand up as an independent new system before rule-based consultation is implemented.

## Delivered chain

- `apps/consultation`
  - participant login and registration
  - consultation preparation form
  - formal-consultation entry state
- `apps/operations-console`
  - admin and researcher login
  - workflow summary
  - doctor persona catalog summary
- `services/identity-service`
  - seeded users
  - SQLite-backed sessions
  - consultation-preparation field storage
- `services/gateway-service`
  - cookie session handling
  - identity proxy
  - workflow resource bootstrap aggregation

## Phase B boundaries

Phase B deliberately does not implement:

- `consultation-service` state machine execution
- scale answering and scoring
- multimodal ingestion
- risk classification
- intervention execution
- follow-up scheduling

Those belong to Phase C and later.

## Current semantic note

- Phase B still persists preparation data through `PUT /api/v1/users/me/profile`.
- The endpoint name is kept for implementation continuity, but its current meaning is “consultation preparation fields”.
- Detailed current-history follow-up and high-risk screening belong to `consultation-service` in Phase C, not to the Phase B preparation form.

## Engineering decisions

- The top-level layout stays close to `aic-coralreef`: `apps / services / packages / infra / docs`
- Each app keeps the same outer shell: `client + server + Dockerfile + README.md + .gitignore + .gitattributes`
- Each backend service keeps the same server template from Phase A, even when Phase B only uses part of it
- Browser configuration is injected through `client/config.js` instead of hardcoding service URLs inside HTML

## Validation

Current local checks:

- Python source under `apps/*/server/app` and `services/*/app` compiles with `py_compile`
- `docker compose -f infra/compose/docker-compose.dev.yml config` passes

Current local limitation:

- the host Python environment does not have `fastapi` installed, so host-side `uvicorn` smoke tests were not executed in this workspace
