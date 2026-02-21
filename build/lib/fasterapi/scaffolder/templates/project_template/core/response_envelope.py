from __future__ import annotations

import inspect
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.responses import Response

_RESPONSE_DOC_ATTR = "__response_doc_config__"


@dataclass(frozen=True)
class ResponseDocConfig:
    message: str
    status_code: int
    description: str
    success_example: Any | None = None
    summary: str | None = None
    include_meta: bool = False
    response_codes: dict[int, str] | None = None
    error_examples: dict[int, Any] | None = None


def success_payload(
    data: Any,
    message: str = "Success",
    *,
    meta: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "success": True,
        "message": message,
        "data": data,
    }
    if meta is not None:
        payload["meta"] = meta
    if request_id:
        payload["requestId"] = request_id
    return payload


def error_payload(
    message: str,
    data: Any = None,
    *,
    request_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "success": False,
        "message": message,
        "data": data,
    }
    if request_id:
        payload["requestId"] = request_id
    return payload


def error_response(
    *,
    status_code: int,
    message: str,
    data: Any = None,
    headers: dict[str, str] | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content=jsonable_encoder(error_payload(message=message, data=data, request_id=request_id)),
    )


def _parse_http_exception_detail(detail: Any) -> tuple[str, Any]:
    if isinstance(detail, str):
        return detail, {"code": "HTTP_EXCEPTION", "details": None}

    if isinstance(detail, dict):
        message = detail.get("message")
        if isinstance(message, str) and message.strip():
            code = detail.get("code", "HTTP_EXCEPTION")
            details = detail.get("details")
            remaining = {k: v for k, v in detail.items() if k not in {"message", "code", "details"}}
            if remaining:
                details = {"extra": remaining, "details": details}
            return message, {"code": code, "details": details}

        nested_detail = detail.get("detail")
        if isinstance(nested_detail, str) and nested_detail.strip():
            return nested_detail, {"code": "HTTP_EXCEPTION", "details": detail}

        return "Request failed", {"code": "HTTP_EXCEPTION", "details": detail}

    if detail is None:
        return "Request failed", {"code": "HTTP_EXCEPTION", "details": None}

    return str(detail), {"code": "HTTP_EXCEPTION", "details": None}


def _extract_request(*args: Any, **kwargs: Any) -> Request | None:
    for value in kwargs.values():
        if isinstance(value, Request):
            return value
    for value in args:
        if isinstance(value, Request):
            return value
    return None


def _request_id_from_request(request: Request | None) -> str | None:
    if request is None:
        return None
    return getattr(request.state, "request_id", None)


def http_exception_response(exc: HTTPException, request: Request | None = None) -> JSONResponse:
    message, data = _parse_http_exception_detail(exc.detail)
    return error_response(
        status_code=exc.status_code,
        message=message,
        data=data,
        request_id=_request_id_from_request(request),
        headers=exc.headers,
    )


def document_response(
    *,
    message: str = "Success",
    status_code: int = status.HTTP_200_OK,
    description: str = "Successful response",
    success_example: Any | None = None,
    summary: str | None = None,
    include_meta: bool = False,
    response_codes: dict[int, str] | None = None,
    error_examples: dict[int, Any] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        config = ResponseDocConfig(
            message=message,
            status_code=status_code,
            description=description,
            success_example=success_example,
            summary=summary,
            include_meta=include_meta,
            response_codes=response_codes,
            error_examples=error_examples,
        )

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Response:
            result = func(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result

            if isinstance(result, Response):
                return result

            meta: dict[str, Any] | None = None
            data = result

            if config.include_meta:
                if isinstance(result, tuple) and len(result) == 2:
                    data, meta = result
                elif isinstance(result, dict) and "items" in result and "meta" in result:
                    data = result.get("items")
                    meta = result.get("meta")

            request = _extract_request(*args, **kwargs)
            request_id = _request_id_from_request(request)

            return JSONResponse(
                status_code=status_code,
                content=jsonable_encoder(
                    success_payload(
                        data=data,
                        message=message,
                        meta=meta,
                        request_id=request_id,
                    )
                ),
            )

        setattr(wrapper, _RESPONSE_DOC_ATTR, config)
        return wrapper

    return decorator


def document_created(*, message: str = "Created", success_example: Any | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    return document_response(
        message=message,
        status_code=status.HTTP_201_CREATED,
        description="Resource created",
        success_example=success_example,
    )


def document_deleted(*, message: str = "Deleted") -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    return document_response(
        message=message,
        status_code=status.HTTP_200_OK,
        description="Resource deleted",
        success_example={"deleted": True},
    )


def document_paginated(
    *,
    message: str = "Success",
    success_example: Any | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    return document_response(
        message=message,
        include_meta=True,
        success_example=success_example if success_example is not None else [],
    )


def apply_response_documentation(app: FastAPI) -> None:
    updated = False

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        config = getattr(route.endpoint, _RESPONSE_DOC_ATTR, None)
        if not isinstance(config, ResponseDocConfig):
            continue

        if config.summary and not route.summary:
            route.summary = config.summary

        route.status_code = config.status_code

        existing_responses = dict(route.responses or {})
        success_code = config.status_code
        response_entry = dict(existing_responses.get(success_code, {}))
        response_entry.setdefault("description", config.description)

        content = dict(response_entry.get("content", {}))
        app_json = dict(content.get("application/json", {}))
        app_json.setdefault(
            "example",
            success_payload(
                data=config.success_example,
                message=config.message,
                meta={"page": 1, "limit": 25} if config.include_meta else None,
            ),
        )
        content["application/json"] = app_json
        response_entry["content"] = content
        existing_responses[success_code] = response_entry

        for code, code_description in (config.response_codes or {}).items():
            entry = dict(existing_responses.get(code, {}))
            entry.setdefault("description", code_description)
            existing_responses[code] = entry

        for code, example in (config.error_examples or {}).items():
            entry = dict(existing_responses.get(code, {}))
            entry.setdefault("description", "Error response")
            entry_content = dict(entry.get("content", {}))
            entry_json = dict(entry_content.get("application/json", {}))
            entry_json.setdefault("example", example)
            entry_content["application/json"] = entry_json
            entry["content"] = entry_content
            existing_responses[code] = entry

        route.responses = existing_responses
        updated = True

    if updated:
        app.openapi_schema = None
