# Procurement Service — Documentation Index

This folder documents the Procurement microservice of the nut_meals backend.
For quick-start / local dev instructions see the top-level `README.md`.

| Doc | Covers |
|---|---|
| [`API.md`](./API.md) | Endpoint reference, request/response shapes, RBAC roles |
| [`SCHEMA.md`](./SCHEMA.md) | Database schema, entity relationships, status lifecycles |
| [`ENV.md`](./ENV.md) | Every environment variable, defaults, and where it's sourced from |
| [`DEPLOYMENT.md`](./DEPLOYMENT.md) | Docker/Compose/CI-CD, OCI Vault secret wiring, rollout process |

Interactive OpenAPI/Swagger docs are served by the running service itself at:

- Swagger UI: `GET /api/v1/docs`
- ReDoc: `GET /api/v1/redoc`
- Raw OpenAPI schema: `GET /api/v1/openapi.json`
