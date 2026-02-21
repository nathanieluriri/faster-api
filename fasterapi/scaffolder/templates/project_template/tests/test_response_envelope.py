from core.response_envelope import error_payload, success_payload


def test_success_payload_includes_meta_and_request_id():
    payload = success_payload(
        data={"value": 1},
        message="ok",
        meta={"page": 1},
        request_id="req-123",
    )
    assert payload["success"] is True
    assert payload["meta"]["page"] == 1
    assert payload["requestId"] == "req-123"




def test_error_payload_includes_request_id():
    payload = error_payload(
        message="failed",
        data={"code": "X"},
        request_id="req-999",
    )
    assert payload["success"] is False
    assert payload["data"]["code"] == "X"
    assert payload["requestId"] == "req-999"







