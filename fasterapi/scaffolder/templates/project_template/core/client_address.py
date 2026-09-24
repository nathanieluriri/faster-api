from starlette.requests import Request


def client_address(request: Request, trusted_proxy_hops: int) -> str:
    # Proxies append to X-Forwarded-For, so everything left of the entries our own proxies added is
    # client-controlled; reading from the left would let callers dodge rate limits with a fake header.
    forwarded = [part.strip() for part in request.headers.get("X-Forwarded-For", "").split(",") if part.strip()]
    if trusted_proxy_hops > 0 and forwarded:
        return forwarded[-trusted_proxy_hops] if len(forwarded) >= trusted_proxy_hops else forwarded[0]
    return request.client.host if request.client else "unknown"
