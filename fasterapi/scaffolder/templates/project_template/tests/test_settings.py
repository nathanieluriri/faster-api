import pytest

from core.settings import get_settings


@pytest.fixture(autouse=True)
def _fresh_settings(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "s" * 40)
    monkeypatch.setenv("SESSION_SECRET_KEY", "t" * 40)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_production_rejects_a_short_super_admin_password(monkeypatch):
    monkeypatch.setenv("SUPER_ADMIN_PASSWORD", "string")
    with pytest.raises(RuntimeError, match="SUPER_ADMIN_PASSWORD"):
        get_settings()


def test_production_allows_a_disabled_super_admin(monkeypatch):
    monkeypatch.setenv("SUPER_ADMIN_PASSWORD", "")
    assert get_settings().is_production
