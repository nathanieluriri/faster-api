from fastapi import Depends, Request

from security.auth import verify_admin_token
from security.principal import AuthPrincipal


async def log_what_admin_does(
    request: Request,
    principal: AuthPrincipal = Depends(verify_admin_token),
) -> None:
    endpoint = request.scope.get("endpoint")
    endpoint_name = endpoint.__name__ if endpoint else "unknown"
    print("admin_id=", principal.user_id, "route=", request.url.path, "function=", endpoint_name)
