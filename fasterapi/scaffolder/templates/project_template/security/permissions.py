from __future__ import annotations

from fastapi import APIRouter
from fastapi.routing import APIRoute

from schemas.imports import Permission, PermissionList


def make_permission_key(*, method: str, path: str) -> str:
    normalized_path = "/" + "/".join(segment for segment in path.strip("/").split("/") if segment)
    return f"{method.upper()}:{normalized_path}"


def _route_permissions(router: APIRouter, *, methods: set[str] | None = None) -> PermissionList:
    permissions: list[Permission] = []
    seen_keys: set[str] = set()

    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue

        route_methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
        for method in route_methods:
            if methods and method not in methods:
                continue

            key = make_permission_key(method=method, path=route.path)
            if key in seen_keys:
                raise ValueError(f"Duplicate permission key detected: {key}")
            seen_keys.add(key)

            permissions.append(
                Permission(
                    name=route.endpoint.__name__,
                    methods=[method],
                    path=route.path,
                    key=key,
                    description=route.description,
                )
            )

    return PermissionList(permissions=permissions)


def get_router_permissions(router: APIRouter) -> PermissionList:
    return _route_permissions(router)


def get_router_get_permissions(router: APIRouter) -> PermissionList:
    return _route_permissions(router, methods={"GET"})


def default_get_permissions() -> PermissionList:
    from api.v1.admin_route import router

    return get_router_get_permissions(router)


def default_permissions() -> PermissionList:
    from api.v1.admin_route import router

    return get_router_permissions(router)
