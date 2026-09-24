from fastapi import APIRouter

from security.permissions import get_endpoint_permissions, get_router_permissions, make_permission_key


def test_make_permission_key_normalizes_path():
    key = make_permission_key(method="get", path="//v1//admins//")
    assert key == "GET:/v1/admins"


def _versioned_router() -> APIRouter:
    router = APIRouter(prefix="/items")

    async def get_my_item():
        return {}

    async def delete_item():
        return {}

    for endpoint in (get_my_item, delete_item):
        endpoint.__module__ = "api.v1.item_route"
    router.add_api_route("/me", get_my_item, methods=["GET"])
    router.add_api_route("/{id}", delete_item, methods=["DELETE"])
    return router


def test_router_permission_keys_include_the_mounted_version_prefix():
    keys = [permission.key for permission in get_router_permissions(_versioned_router()).permissions]
    assert keys == ["GET:/v1/items/me", "DELETE:/v1/items/{id}"]


def test_endpoint_permissions_only_include_named_endpoints():
    permissions = get_endpoint_permissions(_versioned_router(), {"get_my_item"}).permissions
    assert [(p.name, p.key) for p in permissions] == [("get_my_item", "GET:/v1/items/me")]
