<div align="center">
  <img src="https://raw.githubusercontent.com/nathanieluriri/faster-api/main/docs/assets/fasterapi-hero.svg" alt="FasterAPI banner" width="100%" />

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
| `new <name>` | Create a new project in a new folder |
| `new-here` | Scaffold a new project in the current folder |
| `make-schema <name>` | Generate a Pydantic schema |
| `make-crud <name>` | Generate CRUD repository functions |
| `make-service <name>` | Generate service layer template |
| `make-route <name> [--version-mode ...]` | Generate route files with API versioning |
| `make-token-repo [roles...]` | Generate token repository for roles |
| `make-token-deps` | Generate token dependency utilities |
| `mount` | Mount routes into `main.py` |
| `run-d` | Run dev server (`uvicorn main:app --reload`) |
| `update` | Upgrade FasterAPI CLI |

### `new` vs `new-here`

- `fasterapi new <name>` creates a new directory (`./<name>`) and scaffolds the project inside it.
- `fasterapi new-here` scaffolds directly into your current directory (`./`) without creating a new folder.
- `new-here` is safety-checked and will stop if template paths already exist in the current directory.

### Route Versioning Modes

- `highest-number`
- `latest-modified`

### Token Repo Defaults

If no roles are provided to `make-token-repo`, defaults are:

`admin, user, staff, guest-editor`

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
- SQLAlchemy repository generators (PostgreSQL/MySQL)
- Config-driven scaffolding via `fasterapi.yaml`
- CI/CD template generation
- Better Docker/Docker Compose scaffolding
- Shell autocompletion support

## Contributing

```bash
git clone https://github.com/nathanieluriri/faster-api.git
cd faster-api
pip install -e .
pytest
```

Issues and pull requests are welcome.

## License

Licensed under the [MIT License](LICENSE).

© 2026 Nathaniel Uriri
