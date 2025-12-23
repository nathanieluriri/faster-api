
from fastapi import APIRouter
from fastapi.routing import APIRoute
from schemas.imports import Permission, PermissionList


def get_router_permissions(router: APIRouter) -> PermissionList:
    return PermissionList(
        permissions=[
            Permission(
                name=route.endpoint.__name__,
                methods=sorted(route.methods),
                path=route.path,
                description=route.description,
            )
            for route in router.routes
            if isinstance(route, APIRoute)
        ]
    )

 
def get_router_get_permissions(router: APIRouter) -> PermissionList:
    return PermissionList(
        permissions=[
            Permission(
                name=route.endpoint.__name__,
                methods=["GET"],  # explicitly only GET
                path=route.path,
                description=route.description,
            )
            for route in router.routes
            if (
                isinstance(route, APIRoute)
                and "GET" in route.methods
            )
        ]
    )
def default_get_permissions():
    from api.v1.admin_route import router
    return get_router_get_permissions(router)

def default_permissions():
    from api.v1.admin_route import router
    return get_router_permissions(router)