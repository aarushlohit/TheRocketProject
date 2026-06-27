---
name: api-forge
description: 'Design and build production-grade APIs with OpenAPI/Swagger, validation, error handling, rate limiting, and documentation. Use when: API design, REST API, API endpoint, API development, API documentation, OpenAPI, Swagger, FastAPI, Flask API.'
---

# API Forge

Design APIs that are consistent, well-documented, and production-ready.

## API Design Principles

1. **Consistent naming** — use nouns for resources (`/users`, `/orders`), not verbs (`/getUsers`).
2. **Use HTTP methods correctly** — GET (read), POST (create), PUT (replace), PATCH (update), DELETE (remove).
3. **Version your API** — prefix with `/v1/`, `/v2/`.
4. **Use standard status codes** — 200 (OK), 201 (Created), 204 (No Content), 400 (Bad Request), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found), 422 (Validation Error), 500 (Internal Server Error).
5. **Consistent error format**:
   ```json
   {
     "error": {
       "code": "VALIDATION_ERROR",
       "message": "The request body contains invalid fields.",
       "details": [
         { "field": "email", "issue": "must be a valid email address" }
       ]
     }
   }
   ```

## Request Validation

- Validate every input at the API boundary.
- Use schema validation (Pydantic for Python, Zod for TypeScript).
- Return 422 with details for validation failures.

## Authentication & Authorization

- Use token-based auth (JWT, OAuth2) for APIs.
- Never accept plain-text passwords.
- Rate limit by API key or user ID.
- Log all auth failures.

## Documentation

- Use OpenAPI 3.x for API documentation.
- Include request/response examples, error codes, and auth requirements.
- Keep docs in sync with code (auto-generate from annotations).
