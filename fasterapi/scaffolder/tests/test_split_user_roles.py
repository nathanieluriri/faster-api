from __future__ import annotations

import json

import pytest

from fasterapi.scaffolder.split_user_roles import (
    RoleSplitState,
    _build_role_rate_limits_csv,
    _validate_roles,
    _write_state,
)


def test_validate_roles_rejects_reserved_and_duplicates():
    with pytest.raises(Exception):
        _validate_roles(["driver", "admin"])

    with pytest.raises(Exception):
        _validate_roles(["driver", "driver"])


def test_validate_roles_accepts_snake_case_roles():
    roles = _validate_roles(["driver", "rider_support"])
    assert roles == ["driver", "rider_support"]


def test_build_role_rate_limits_csv_orders_expected_roles():
    result = _build_role_rate_limits_csv(["driver", "rider"])
    assert result == "anonymous:20/minute,driver:80/minute,rider:80/minute,admin:140/minute"


def test_write_state_round_trip_payload(tmp_path):
    state = RoleSplitState(
        version=1,
        mode="split",
        roles=("driver", "rider"),
        previous_primary_role="user",
        created_at="2026-02-22T00:00:00+00:00",
        touched_files=("security/auth.py", "main.py"),
        archived_at="20260222T000000Z",
        last_unsplit_at=None,
    )

    _write_state(tmp_path, state)
    content = json.loads((tmp_path / ".fasterapi" / "role_split_state.json").read_text(encoding="utf-8"))
    assert content["mode"] == "split"
    assert content["roles"] == ["driver", "rider"]
    assert content["touched_files"] == ["security/auth.py", "main.py"]
