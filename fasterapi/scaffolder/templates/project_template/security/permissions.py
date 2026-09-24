from __future__ import annotations

from fastapi import APIRouter
from fastapi.routing import APIRoute

from schemas.imports import Permission, PermissionList


def make_permission_key(*, method: str, path: str) -> str:
    normalized_path = "/" + "/".join(segment for segment in path.strip("/").split("/") if segment)
    return f"{method.upper()}:{normalized_path}"


def _mount_prefix(route: APIRoute) -> str:
    # `fasterapi mount` includes routers from api/<version>/ under /<version>, and requests are checked
    # against that full path, so keys built from the router alone would never match.
    parts = route.endpoint.__module__.split(".")
    return f"/{parts[1]}" if len(parts) >= 3 and parts[0] == "api" else ""


def _route_permissions(
    router: APIRouter,
    *,
    methods: set[str] | None = None,
    endpoints: set[str] | None = None,
) -> PermissionList:
    permissions: list[Permission] = []
    seen_keys: set[str] = set()

    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        if endpoints is not None and route.endpoint.__name__ not in endpoints:
            continue

        path = _mount_prefix(route) + route.path
        route_methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
        for method in route_methods:
            if methods and method not in methods:
                continue

            key = make_permission_key(method=method, path=path)
            if key in seen_keys:
                raise ValueError(f"Duplicate permission key detected: {key}")
            seen_keys.add(key)

            permissions.append(
                Permission(
                    name=route.endpoint.__name__,
                    methods=[method],
                    path=path,
                    key=key,
                    description=route.description,
                )
            )

    return PermissionList(permissions=permissions)


def get_router_permissions(router: APIRouter) -> PermissionList:
    return _route_permissions(router)


def get_router_get_permissions(router: APIRouter) -> PermissionList:
    return _route_permissions(router, methods={"GET"})


def get_endpoint_permissions(router: APIRouter, endpoints: set[str]) -> PermissionList:
    return _route_permissions(router, endpoints=endpoints)


def default_get_permissions() -> PermissionList:
    from api.v1.admin_route import router

    return get_router_get_permissions(router)


def default_permissions() -> PermissionList:
    from api.v1.admin_route import router

    return get_router_permissions(router)
