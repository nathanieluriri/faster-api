# Future Plan: Response Envelope and API Quality Roadmap

## Goal
Make the new envelope system production-grade, predictable, and easy for contributors to extend.

Envelope target:
```json
{
  "success": true,
  "message": "Success",
  "data": {}
}
```

## Phase 1: Lock the Contract (High Priority)
- Standardize envelope fields for all JSON routes:
  - Success: `success`, `message`, `data`
  - Error: `success`, `message`, `data` (with structured error details)
- Add optional `meta` block for pagination/list endpoints.
- Add optional `requestId` field for traceability.
- Define a strict error shape in `data`:
  - `code` (machine readable)
  - `details` (field-level or domain-level details)
- Keep redirects/file streams excluded from envelope by design and document this clearly.

Acceptance criteria:
- 100% JSON endpoints use one envelope contract.
- No endpoint returns `status_code/detail` in body anymore.

## Phase 2: Improve the Decorator API
- Extend `@document_response(...)` to support:
  - `error_examples`
  - `response_codes` map (e.g. `200`, `201`, `204`, `400`, `404`, `409`, `422`)
  - optional `tags`/`summary`/`description` passthrough
- Add `@document_response(..., include_meta=True)` behavior for list endpoints.
- Add helper decorators for common patterns:
  - `@document_created(...)`
  - `@document_deleted(...)`
  - `@document_paginated(...)`

Acceptance criteria:
- New endpoints can be fully documented with one decorator call.
- Generated OpenAPI includes realistic examples for both success and failures.

## Phase 3: Error Handling Hardening
- Add centralized error-code registry (constants/enums), e.g.:
  - `AUTH_INVALID_TOKEN`
  - `RESOURCE_NOT_FOUND`
  - `VALIDATION_FAILED`
- Map common exceptions to stable HTTP + error code.
- Avoid leaking internal exception text in production; gate by environment.
- Normalize validation errors to consistent `data.details` format.

Acceptance criteria:
- Same error condition always returns same status and error code.
- Production responses do not expose stack/internal messages.

## Phase 3.5: Authentication and Authorization Hardening (Admin + API Checks)
- Normalize auth dependency return types:
  - `verify_admin_token` should return one consistent typed object (not mixed dict/model behavior).
  - Route handlers and security checks should use the same token field access style.
- Fix admin account deletion auth path:
  - Use admin principal from admin verifier in handler params.
  - Remove member-token dependency from admin delete handler.
- Add role-specific refresh token verification:
  - Admin refresh route must validate admin role explicitly.
  - User refresh route must validate member role explicitly.
  - Ensure expired access token role matches refresh-token owner role.
- Eliminate duplicate auth dependency execution:
  - Avoid attaching the same verifier both in route `dependencies=[...]` and parameter `Depends(...)`.
  - Reuse resolved principal via one dependency chain.
- Harden permission checks:
  - Stop keying permissions only by endpoint function name.
  - Use stable permission keys (e.g. route path + method + explicit permission id).
  - Add startup validation to detect duplicate/missing permission definitions.
- Add a unified auth error policy:
  - Use consistent `401` vs `403` semantics.
  - Return consistent auth error codes (e.g. `AUTH_INVALID_TOKEN`, `AUTH_ROLE_MISMATCH`, `AUTH_ACCOUNT_INACTIVE`, `AUTH_PERMISSION_DENIED`).
- Strengthen token lifecycle checks:
  - Standardize access-token expiry/rotation behavior for both admin and member.
  - Add replay/rotation checks for refresh flow and revoke old token pairs reliably.
- Expand audit logs for admin-protected routes:
  - Log auth principal id, route, method, result (allow/deny), and denial reason code.

Acceptance criteria:
- Admin routes cannot be accessed with member principals or mixed-role refresh flows.
- Admin delete, profile, list, signup, and refresh use one coherent auth dependency pattern.
- Permission checks remain stable even if endpoint function names are refactored.
- Auth test suite covers positive and negative role/permission/account-status cases.

## Phase 4: Testing and Contract Safety
- Add response contract tests for all template routes:
  - success envelope shape
  - error envelope shape
  - status code correctness (`201` create, etc.)
- Add snapshot tests for generated OpenAPI schema.
- Add scaffolder generation tests verifying new routes include decorator + envelope behavior.

Acceptance criteria:
- CI fails if envelope contract drifts.
- OpenAPI changes are intentional and reviewed.

## Phase 5: Generator and Template Completeness
- Ensure all generators (account/crud/custom routes) emit the new decorator pattern by default.
- Ensure generated examples include realistic payloads.
- Add guidance in template README for how to use `@document_response`.
- Add one migration guide section: "Legacy responses -> envelope responses".

Acceptance criteria:
- Freshly scaffolded projects need zero manual edits to follow envelope standard.

## Phase 6: Observability and Operations
- Add middleware to attach/generate `requestId` (propagate from header if provided).
- Log envelope failures with request id and endpoint metadata.
- Add metrics counters for:
  - success/failure rates by route
  - error codes by route
  - validation error frequency

Acceptance criteria:
- Every production error can be traced quickly with `requestId`.

## Phase 7: DX and Governance
- Add lint rule/check script for envelope usage:
  - disallow plain dict success responses in API routes unless wrapped/decorated
- Add PR checklist item: "Envelope + status code + examples updated".
- Add release-note section template for API contract changes.

Acceptance criteria:
- New contributors can follow one clear pattern without tribal knowledge.

## Suggested Immediate Next 5 Tasks
1. Add `requestId` support to envelope + middleware.
2. Add `code` + `details` structure to all error responses.
3. Extend `document_response` to declare non-2xx responses.
4. Add tests for status code rules (`201`, `200`, `422`, `404`, `429`).
5. Update template README with a short "Response Envelope" section and examples.
