from terminal_app.api.response import error, ok


def test_ok_envelope_shape():
    out = ok({"x": 1}, {"count": 1})
    assert out["status"] == "ok"
    assert "timestamp" in out
    assert out["data"]["x"] == 1
    assert out["meta"]["count"] == 1


def test_error_envelope_shape():
    out = error("bad", "failed")
    assert out["status"] == "error"
    assert out["error"]["code"] == "bad"
    assert out["error"]["detail"] == "failed"
