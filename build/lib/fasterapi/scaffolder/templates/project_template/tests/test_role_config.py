from core.role_config import (
    build_role_rate_limits,
    build_role_rate_limits_csv,
    normalize_role,
    parse_role_rate_limits,
)


def test_normalize_role_maps_member_to_user():
    assert normalize_role("member") == "user"
    assert normalize_role("user") == "user"


def test_parse_role_rate_limits_ignores_invalid_tokens():
    parsed = parse_role_rate_limits("anonymous:20/minute,invalid,driver:70/minute")
    assert parsed["anonymous"] == "20/minute"
    assert parsed["driver"] == "70/minute"
    assert "invalid" not in parsed


def test_build_role_rate_limits_uses_fallback_and_has_anonymous():
    fallback_csv = build_role_rate_limits_csv(non_admin_roles=["driver", "rider"])
    rules = build_role_rate_limits(raw=None, fallback_csv=fallback_csv)
    assert "anonymous" in rules
    assert "driver" in rules
    assert "rider" in rules
    assert "admin" in rules
