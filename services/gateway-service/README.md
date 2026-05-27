# Gateway Service

`gateway-service` is the Phase B browser-facing BFF.

Responsibilities:

- proxy identity APIs for browser clients
- terminate session token into `mcs_session` cookie
- read workflow resources from `packages/workflow-resources`
- aggregate bootstrap data for frontend shells
- proxy consultation live snapshot and SSE stream for realtime dashboard consumers

## Current API

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/users/me`
- `PUT /api/v1/users/me/profile`
- `POST /api/v1/consultations`
- `GET /api/v1/consultations/{id}`
- `POST /api/v1/consultations/{id}/start`
- `POST /api/v1/consultations/{id}/turns`
- `GET /api/v1/consultations/{id}/multimodal/live`
- `GET /api/v1/consultations/{id}/multimodal/live/stream`
- `GET /api/v1/consultations/{id}/turns/{turn_id}/multimodal/bundle`
- `GET /api/v1/assessment/catalog`
- `POST /api/v1/assessment/sessions`
- `GET /api/v1/assessment/sessions/{id}`
- `POST /api/v1/assessment/sessions/{id}/answers`
- `GET /api/v1/catalog/doctor-personas`
- `GET /api/v1/catalog/workflow-summary`
- `GET /api/v1/system/bootstrap`

## Environment

- `IDENTITY_SERVICE_URL`
- `CONSULTATION_SERVICE_URL`
- `ASSESSMENT_SERVICE_URL`
- `SESSION_COOKIE_NAME`
- `WORKFLOW_RESOURCES_DIR`
- `CORS_ORIGINS`

See `.env.example` for defaults.
