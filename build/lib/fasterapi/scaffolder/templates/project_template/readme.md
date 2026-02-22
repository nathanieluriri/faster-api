# FasterAPI Project Template

This scaffold is a production-ready FastAPI starter with:

- Envelope-based API responses (`success`, `message`, `data`, optional `meta`, `requestId`)
- Typed auth principal dependencies (user/admin)
- Queue abstraction with singleton manager (Celery-first)
- Document upload abstraction (local + S3)
- Payment abstraction (Flutterwave + Stripe)
- Email abstraction with singleton manager, retries, logging, and queue-ready dispatch

## Environment

Copy `.env.example` to `.env` and set required values.

Key variables:

- `SECRET_KEY`, `SESSION_SECRET_KEY`
- `MONGO_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `ROLE_RATE_LIMITS` (example: `anonymous:20/minute,user:80/minute,admin:140/minute`)
- `STORAGE_BACKEND` (`local` or `s3`)
- `PAYMENT_DEFAULT_PROVIDER` (`flutterwave` or `stripe`)
- Provider secrets (`FLUTTERWAVE_SECRET_KEY`, `STRIPE_SECRET_KEY`)
- Email settings (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USERNAME`, `EMAIL_PASSWORD`)

## Email Workflow

- Built-in project default: `email_templates/starter_template.py`
- Add more templates with CLI: `fasterapi email add-template`
- Mount templates into the singleton registry: `fasterapi email mount`
- Mount custom templates from `custom_templates/`: `fasterapi email mount-custom`

If mount fails, read `email_mount_errors.log` in your project root.

## New API Modules

- `GET/POST/DELETE /v1/documents/*`
- `POST/GET /v1/payments/*`

## Queue Usage

Use the queue manager instead of calling Celery directly:

```python
from core.queue.manager import QueueManager

QueueManager.get_instance().enqueue("delete_tokens", {"userId": user_id})
```

## Response Documentation

Use `document_response` helpers in routes:

- `@document_response(...)`
- `@document_created(...)`
- `@document_deleted(...)`
- `@document_paginated(...)`
