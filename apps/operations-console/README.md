# Operations Console

`operations-console` follows the `aic-coralreef` app envelope:

- `client/`: static browser shell for admin and researcher users
- `server/`: FastAPI static-file host for the client
- root `Dockerfile`: builds the app as one deployable unit

## Phase B scope

Current frontend flow:

1. login as `admin` or `researcher`
2. read workflow summary
3. read doctor persona catalog summary for the current workflow

This app is intentionally limited in Phase B. It is only the minimal management shell needed to verify identity, role, and workflow bootstrap data.

## Runtime config

- browser API base is read from `client/config.js`
- default value: `http://127.0.0.1:8080/api/v1`

## Related docs

- `../../docs/operations/phase-b-runbook.md`
- `../../docs/architecture/phase-b-implementation.md`
