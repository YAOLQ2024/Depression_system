# Identity Service

`identity-service` is the Phase B source of truth for:

- user registration
- login and logout
- role assignment
- session token storage
- consultation-preparation fields

## Current storage model

- PostgreSQL
- Alembic schema migrations
- users table
- sessions table

Default seed accounts:

- `admin@mcs.local / Admin123!`
- `researcher@mcs.local / Research123!`
- `participant@mcs.local / Participant123!`

## Current API

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/roles`
- `GET /api/v1/users/me`
- `PUT /api/v1/users/me/profile`

## Semantic note

- the endpoint name `/api/v1/users/me/profile` is temporarily kept
- in the new workflow it currently stores preparation fields used before formal digital-human consultation starts
- full current-history follow-up and high-risk screening do not belong here

## Environment

- `DATABASE_URL`
- `CORS_ORIGINS`
- `SESSION_TTL_HOURS`

See `.env.example` for defaults.

## Startup behavior

- container startup runs `alembic upgrade head`
- FastAPI startup seeds the default admin, researcher, and participant accounts
