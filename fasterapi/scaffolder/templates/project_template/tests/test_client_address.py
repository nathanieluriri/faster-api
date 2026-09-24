from starlette.requests import Request

from core.client_address import client_address


def _request(forwarded: str | None = None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "headers": headers, "client": ("198.51.100.7", 4321)})


def test_uses_the_entry_appended_by_the_trusted_proxy():
    assert client_address(_request("6.6.6.6, 203.0.113.9"), trusted_proxy_hops=1) == "203.0.113.9"
    assert client_address(_request("6.6.6.6, 203.0.113.9, 35.0.0.1"), trusted_proxy_hops=2) == "203.0.113.9"


def test_ignores_the_header_without_trusted_proxies():
    assert client_address(_request("6.6.6.6"), trusted_proxy_hops=0) == "198.51.100.7"
    assert client_address(_request(), trusted_proxy_hops=1) == "198.51.100.7"
