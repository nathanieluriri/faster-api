# Future Plan: `split-user` / `unsplit-user` Role Conversion

Date: 2026-02-22

## Goal

Add a CLI workflow that can:

1. Split the existing `user` module into multiple role-specific modules (for example `driver` and `rider`) with distinct auth dependencies.
2. Convert a split system back to a single `user` role when needed.
3. Keep rate limiting correct after either conversion.

## What Currently Exists

- `fasterapi make-account <name>` can clone user-style scaffolding into one new role file set (`schema/repo/service/route`).
- `fasterapi make-token-repo <roles...>` can generate role-specific token repository helpers.
- Auth is currently hardcoded to `member` and `admin` in scaffold templates:
  - `security/auth.py`
  - `security/principal.py`
  - token issuance helpers and JWT shortcuts.
- Rate limiting is currently hardcoded to:
  - `anonymous`
  - `member`
  - `admin`

## Gaps

- No command exists to transform existing `user_*` into a role matrix end-to-end.
- No reverse command exists to collapse roles back into one `user` role.
- Auth dependency functions are role-name-specific and not generated dynamically.
- Rate limits are not role-configurable from split workflow.

## Proposed New Commands

## `fasterapi split-user`

Interactive flow (exact UX requirement):

1. Prompt: `Split user to what?`
2. User types first role (example: `driver`).
3. Show option: `1. Enter name of the next role`.
4. After second role is entered (example: `rider`), show:
   - `1. Enter name of next role`
   - `2. Type end to convert to split into driver and rider`
5. If user chooses `1`, continue collecting roles.
6. If user types `end`, run conversion with collected roles.

Validation rules:

- Minimum roles required before `end`: 2.
- Role names must be lowercase snake-case (letters, numbers, underscore).
- Reserved names blocked: `admin`, `anonymous`, `member`, `user` (for split target list).
- Duplicate role names blocked.

## `fasterapi unsplit-user`

Interactive flow:

1. Detect split state and list existing custom roles.
2. Prompt confirmation to collapse back to `user`.
3. Apply conversion and keep backups of affected files.

Validation rules:

- If no split roles are detected, abort with clear message.
- Require explicit confirmation before destructive rewrites.

## Design Approach

Create a new scaffolder module:

- `fasterapi/scaffolder/split_user_roles.py`

Expose two entry points:

- `run_split_user_wizard()`
- `run_unsplit_user_wizard()`

Register both in `fasterapi/cli.py`.

## Split Conversion Plan (Implementation TODO)

- [ ] Add role collection wizard implementing the exact prompt/options flow above.
- [ ] Add state file to track role conversion metadata, for example:
  - `.fasterapi/role_split_state.json`
- [ ] Generate role module files for each role:
  - `schemas/<role>_schema.py`
  - `repositories/<role>_repo.py`
  - `services/<role>_service.py`
  - `api/v1/<role>_route.py`
- [ ] Reuse `generate_account._apply_replacements` style logic, but avoid blind replacements by adding AST/token-safe replacements for critical auth imports.
- [ ] Regenerate token repository with provided roles by calling `make-token-repo` scaffolder internals.
- [ ] Refactor auth templates from fixed role checks to role-aware generic helpers:
  - generate `verify_<role>_token`
  - generate `verify_<role>_refresh_token`
  - keep `verify_any_token`.
- [ ] Update principal role typing from fixed literal to generated literal union of active roles.
- [ ] Update JWT/token helper functions to generic role-based issuance path.
- [ ] Update routes to depend on the correct generated role verifier per role module.
- [ ] Update/remove legacy `user` route wiring as part of split mode.
- [ ] Write migration report to project root:
  - `split_user_report.md`

## Unsplit Conversion Plan (Implementation TODO)

- [ ] Read split state file to know active roles and touched files.
- [ ] Rebuild canonical `user` files from user templates:
  - `user_schema.py`, `user_repo.py`, `user_service.py`, `user_route.py`
- [ ] Reset auth templates to single user-role mode (`user`) plus optional `admin`.
- [ ] Regenerate token repository for unsplit role set.
- [ ] Repoint route dependencies and imports back to user paths.
- [ ] Keep archived split files in a safe folder:
  - `.fasterapi/archive/<timestamp>/...`
- [ ] Write migration report:
  - `unsplit_user_report.md`

## Rate Limiting Plan

Rate limiting must not remain hardcoded.

Implementation:

- [ ] Introduce dynamic role rate map loader in scaffold `main.py`.
- [ ] Add new env variable format, for example:
  - `ROLE_RATE_LIMITS=anonymous:20/minute,driver:80/minute,rider:80/minute,admin:140/minute`
- [ ] During split, auto-update `.env.example` defaults to include selected roles.
- [ ] During unsplit, reset defaults to `anonymous,user,admin` profile.
- [ ] Preserve backward compatibility:
  - if dynamic config missing, fall back to safe defaults.

Validation tests:

- [ ] Unknown token role resolves to `anonymous` limiter.
- [ ] New roles from split get the configured limit.
- [ ] `429` headers still include limit/remaining/reset fields.

## Keep / Remove / Refactor Matrix

Keep:

- `make-account` as low-level building block for generating role files.
- `make-token-repo` as backend generator (can be called internally by split/unsplit).
- `verify_any_token` concept.

Refactor:

- `security/auth.py`: remove hardcoded `{member, admin}` checks and generate role-aware verifier functions.
- `security/principal.py`: replace fixed role literal with generated role union.
- `services/auth_helpers.py`: replace admin/member branching with generic `issue_tokens_for_role`.
- `security/encrypting_jwt.py`: replace role-specific token creator helpers with a generic role function.

Remove (or deprecate):

- Hardcoded aliases tied to member/admin naming where no longer useful after role generation.
- Any stale generated functions for roles no longer present after unsplit.

## Safety and Idempotency

- [ ] Every conversion writes backups before file mutation.
- [ ] Re-running `split-user` with same roles should be idempotent.
- [ ] Re-running `unsplit-user` in unsplit state should no-op cleanly.
- [ ] Abort when local files have unresolved conflicts unless `--force` is explicitly used.

## Tests

- [ ] Unit tests for wizard role collection and validation.
- [ ] Unit tests for file rewrite planners (split and unsplit).
- [ ] Integration test: split into `driver,rider`, then unsplit back to `user`.
- [ ] Integration test: split with 3+ roles.
- [ ] Integration test: rate limit behavior for new roles.
- [ ] Regression tests for existing `admin` flows.

## Acceptance Criteria

- `fasterapi split-user` can convert to at least 2 roles from interactive prompts.
- Generated roles have distinct auth dependencies and working token issuance.
- `fasterapi unsplit-user` restores single user-role setup safely.
- Rate limiting works for generated roles and fallback paths.
- Reports are written for both split and unsplit operations.
- Command errors are actionable and non-destructive by default.
