# FasterAPI Project Template

This scaffold is a production-ready FastAPI starter with:

- Envelope-based API responses (`success`, `message`, `data`, optional `meta`, `requestId`)
- Typed auth principal dependencies (member/admin)
- Queue abstraction with singleton manager (Celery-first)
- Document upload abstraction (local + S3)
- Payment abstraction (Flutterwave + Stripe)

## Environment

Copy `.env.example` to `.env` and set required values.

Key variables:

- `SECRET_KEY`, `SESSION_SECRET_KEY`
- `MONGO_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `STORAGE_BACKEND` (`local` or `s3`)
- `PAYMENT_DEFAULT_PROVIDER` (`flutterwave` or `stripe`)
- Provider secrets (`FLUTTERWAVE_SECRET_KEY`, `STRIPE_SECRET_KEY`)

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
