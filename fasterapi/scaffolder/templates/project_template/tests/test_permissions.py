from security.permissions import make_permission_key

def test_make_permission_key_normalizes_path():
    key = make_permission_key(method="get", path="//v1//admins//")
    assert key == "GET:/v1/admins"
