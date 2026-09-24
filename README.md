<div align="center">
  <img src="https://pub-4e784ee4f6b24479b0e9573fac4a96e8.r2.dev/branding/697a6159f4c5b5ab4a04c6c5/anagramlightmodeurl_0b524763f9a54c75a46708152a9d5df3.png" alt="FasterAPI banner" width="100%" />

  <h1>FasterAPI</h1>
  <p><strong>Scaffold FastAPI APIs faster with a focused CLI for backend teams.</strong></p>

  <p>
    <a href="https://pypi.org/project/nats-fasterapi/"><img src="https://img.shields.io/pypi/v/nats-fasterapi?label=PyPI&color=0A66C2" alt="PyPI Version" /></a>
    <a href="https://pypi.org/project/nats-fasterapi/"><img src="https://img.shields.io/pypi/pyversions/nats-fasterapi" alt="Python Versions" /></a>
    <a href="LICENSE"><img src="https://img.shields.io/github/license/nathanieluriri/faster-api" alt="License" /></a>
    <a href="https://pypi.org/project/nats-fasterapi/"><img src="https://img.shields.io/pypi/dm/nats-fasterapi" alt="Monthly Downloads" /></a>
    <a href="https://github.com/nathanieluriri/faster-api"><img src="https://img.shields.io/github/last-commit/nathanieluriri/faster-api" alt="Last Commit" /></a>
  </p>

  <p>
    <a href="#quick-start"><strong>Quick Start</strong></a>
    ·
    <a href="#demo"><strong>Demo</strong></a>
    ·
    <a href="#command-reference"><strong>Command Reference</strong></a>
    ·
    <a href="#contributing"><strong>Contributing</strong></a>
  </p>
</div>

## Why FasterAPI

`nats-fasterapi` helps you skip repetitive setup and move straight to business logic.

- Generate Pydantic schemas with one command
- Generate CRUD repositories and service layers
- Generate versioned FastAPI routes quickly
- Generate token repository and auth dependency utilities
- Auto-mount routes into `main.py`
- Works in interactive and automation-friendly flows

## Demo

<p align="center">
  <img src="https://raw.githubusercontent.com/nathanieluriri/faster-api/main/docs/assets/fasterapi-demo.gif" alt="FasterAPI CLI demo" width="100%" />
</p>

## CLI Preview Screens

<p align="center">
  <img src="https://raw.githubusercontent.com/nathanieluriri/faster-api/main/docs/assets/terminal-shot-generate.svg" alt="Generating schema CRUD service and route" width="100%" />
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/nathanieluriri/faster-api/main/docs/assets/terminal-shot-help.svg" alt="FasterAPI help output screenshot" width="100%" />
</p>

## Installation

```bash
pip install nats-fasterapi
```

Upgrade:

```bash
fasterapi update
```

## Quick Start

```bash
# 1) Create a schema
fasterapi make-schema user

# 2) Generate repository and service
fasterapi make-crud user
fasterapi make-service user

# 3) Generate a versioned route
fasterapi make-route user --version-mode highest-number

# 4) Mount routes into main.py
fasterapi mount
```

Run the app in development mode:

```bash
fasterapi run-d
```

## Command Reference

| Command | Purpose |
| --- | --- |
| `new <name> [--db ...] [--deploy ...]` | Create a new project in a new folder |
| `new-here [--db ...] [--deploy ...]` | Scaffold a new project in the current folder |
| `db use <mongodb\|postgres\|supabase>` | Switch an existing project's database |
| `deploy check --target <vercel\|cloudrun>` | List features and settings that won't work on the platform |
| `deploy init <vercel\|cloudrun>` | Add `vercel.json`, or a Cloud Run ready Dockerfile and ignore files |
| `deploy vercel [--prod] [--push-env]` | Check, then deploy with the Vercel CLI |
| `deploy cloudrun --service <name>` | Check, then deploy to Cloud Run from source |
| `make-schema <name>` | Generate a Pydantic schema |
| `make-crud <name>` | Generate CRUD repository functions |
| `make-service <name>` | Generate service layer template |
| `make-route <name> [--version-mode ...]` | Generate route files with API versioning |
| `make-account <name>` | Add a new account type (e.g. `customer`) with its own signup, login, tokens and permission checks |
| `make-token-repo [roles...]` | Generate token repository for roles |
| `split-user [--force]` | Interactively split `user` into custom non-admin roles |
| `unsplit-user [--force]` | Collapse split custom roles back into canonical `user` |
| `mount` | Mount routes into `main.py` |
| `email add-template` | Interactively add a built-in email template example |
| `email mount` | Mount templates from `email_templates/` into the email singleton |
| `email mount-custom` | Move templates from `custom_templates/` and mount them |
| `run-d` | Run dev server (`uvicorn main:app --reload`) |
| `update` | Upgrade FasterAPI CLI |

### `new` vs `new-here`

- `fasterapi new <name>` creates a new directory (`./<name>`) and scaffolds the project inside it.
- `fasterapi new-here` scaffolds directly into your current directory (`./`) without creating a new folder.
- `new-here` is safety-checked and will stop if template paths already exist in the current directory.

## Databases

Projects use MongoDB by default. Postgres, Supabase and Neon are supported through a built-in
Postgres backend that speaks the same API as the MongoDB driver, so the built-in auth, tokens,
payments and every generated repository work unchanged.

```bash
fasterapi new shop --db supabase     # or --db postgres
fasterapi db use postgres            # switch an existing project
```

Then set `DATABASE_URL` in `.env`. Each collection becomes a table with a JSONB column, created
on first use. Tables get row level security enabled, so Supabase's public REST API can't read them.

- Supported queries: equality, dotted paths, `$and`, `$or`, `$eq`, `$ne`, `$gt`, `$gte`, `$lt`,
  `$lte`, `$in`, `$nin`, `$exists`, plus `sort`, `skip`, `limit` and projections.
- Supported updates: `$set`, `$unset`, `$inc`.
- Anything else (for example `$regex` or `aggregate`) raises a clear `NotImplementedError`.
- On Vercel or other serverless hosts, use Supabase's transaction pooler URL (port 6543).

## Accounts and Permissions

- New users (email signup or Google sign-in) can view and delete their own account:
  `GET /v1/users/me` and `DELETE /v1/users/account`. Admins grant anything else.
  Permissions or an account status sent in a signup request are ignored.
- Roles created with `split-user` or `make-account` get the same defaults for their own routes.
  `make-account` roles are kept when you later run `split-user` or `unsplit-user`.
- Invited admins can view and delete their own account. An inviting admin can only grant
  permissions they hold themselves.
- Admins manage every account type from `/v1/admins/accounts/{role}`: list accounts, see the
  permissions that can be granted (`/permissions`), and `PATCH /{account_id}` to set
  `permissionList` or `accountStatus`. Suspending an account ends its sessions immediately.
- Passwords need at least 8 characters. Accounts created through Google can't be opened with a
  password, and Google sign-in never takes over an account that was registered with a password.
- After Google sign-in, users are redirected to `SUCCESS_PAGE_URL` with the tokens in the URL
  fragment (`#access_token=...&refresh_token=...`), so read them from `window.location.hash`.
  Failures go to `ERROR_PAGE_URL?error=...`.
- The built-in super admin has every admin permission and is how you invite the first admins.
  Set `SUPER_ADMIN_EMAIL` and `SUPER_ADMIN_PASSWORD` to enable it; production requires a
  password of at least 12 characters, and `deploy check` flags shorter ones.

### Rate limiting behind a proxy

Anonymous requests are rate limited by client IP, read from `X-Forwarded-For`. Only the entries
your own proxies append are trusted, so a forged header can't dodge the limit. Set
`TRUSTED_PROXY_HOPS` to the number of proxies in front of the app: `1` for Vercel, Cloud Run,
Render, Fly or nginx (the default), `2` behind a Google Cloud external load balancer, `0` when
clients connect directly.

## Deploying

```bash
fasterapi new shop --db supabase --deploy vercel     # or --deploy cloudrun
fasterapi deploy check --target vercel               # exits 1 on blocking problems, CI friendly
fasterapi deploy vercel --prod --push-env
fasterapi deploy cloudrun --service shop-api --region us-central1
```

`deploy check` reads `.env` (or `--env-file`) and scans your code. It reports, with file and
line where relevant:

| Feature | Vercel | Cloud Run |
| --- | --- | --- |
| Local database or Redis host, empty secrets | error | error |
| `STORAGE_BACKEND=local` uploads | error (read-only disk) | warning (disk wiped on scale down) |
| APScheduler jobs | error (no long-running process) | warning (CPU throttled, scales to zero) |
| Celery queue and `EMAIL_QUEUE_ENABLED=true` | error (no workers) | warning (needs a worker service) |
| WebSocket endpoints | error | supported |
| `BackgroundTasks` | warning | warning |
| Supabase direct connection (port 5432) | warning | fine |

Cloud Run deploys default to scale to zero (`--min-instances 0`) and cap at `--max-instances 3`,
so idle time costs nothing and traffic spikes can't run up the bill. `deploy init` and
`--deploy` also turn off the scheduler and email queue in your env files, since neither works
without a long-running worker.

### Route Versioning Modes

- `highest-number`
- `latest-modified`

### Token Repo Defaults

If no roles are provided to `make-token-repo`, defaults are:

`admin, user`

### Email Templates

`fasterapi email add-template` first asks what kind of template you need, then shows available examples.

Built-in examples (10):

- `changing-password`
- `invitation`
- `new-signin`
- `otp`
- `revoking`
- `welcome`
- `password-reset`
- `email-verification`
- `receipt`
- `account-deactivated`

Then mount templates with:

```bash
fasterapi email mount
```

For custom files placed in `custom_templates/`:

```bash
fasterapi email mount-custom
```

If mounting fails, check `email_mount_errors.log` in the project root.

## Typical Workflow

```bash
fasterapi make-schema product
fasterapi make-crud product
fasterapi make-service product
fasterapi make-route product --version-mode latest-modified
fasterapi mount
fasterapi run-d
```

## Roadmap

- Improve `new` and `new-here` bootstrap customization
- MySQL support
- Config-driven scaffolding via `fasterapi.yaml`
- CI/CD template generation
- Better Docker/Docker Compose scaffolding
- Shell autocompletion support

## Contributing

```bash
git clone https://github.com/nathanieluriri/faster-api.git
cd faster-api
pip install -e . pytest
pytest
# Postgres and end-to-end tests run when a database and Redis are available:
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test TEST_REDIS_URL=redis://localhost:6379/0 pytest
```

Issues and pull requests are welcome.

## License

Licensed under the [MIT License](LICENSE).

© 2026 Nathaniel Uriri
