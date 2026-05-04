# Consultation

`consultation` follows the `aic-coralreef` app envelope:

- `client/`: static browser shell for Phase B
- `server/`: FastAPI static-file host for the client
- root `Dockerfile`: builds the app as one deployable unit

## Phase B scope

Current frontend flow:

1. register or login as participant
2. complete consultation preparation information
3. reach the formal-consultation entry state

Phase B stops at the entry of rule-based consultation. The actual “数字人交互问诊” state machine belongs to Phase C and will be implemented in `consultation-service`.

## Runtime config

- browser API base is read from `client/config.js`
- default value: `http://127.0.0.1:8080/api/v1`

## Related docs

- `../../docs/operations/phase-b-runbook.md`
- `../../docs/architecture/phase-b-implementation.md`
