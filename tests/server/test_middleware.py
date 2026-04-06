import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from atlas.server.middleware import add_middleware, AtlasErrorHandler


def _create_test_app() -> FastAPI:
    app = FastAPI()
    add_middleware(app)

    @app.get("/ok")
    def ok_endpoint():
        return {"status": "ok"}

    @app.get("/fail")
    def fail_endpoint():
        raise ValueError("Something went wrong")

    @app.get("/404")
    def not_found_endpoint():
        from atlas.server.middleware import AtlasNotFoundError
        raise AtlasNotFoundError("Page not found")

    @app.get("/400")
    def bad_request_endpoint():
        from atlas.server.middleware import AtlasValidationError
        raise AtlasValidationError("Invalid input")

    return app


def test_cors_headers():
    app = _create_test_app()
    client = TestClient(app)
    resp = client.options("/ok", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers


def test_ok_response():
    app = _create_test_app()
    client = TestClient(app)
    resp = client.get("/ok")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_unhandled_error_returns_500():
    app = _create_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/fail")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"] == "internal_error"
    assert "Something went wrong" in body["detail"]


def test_not_found_error_returns_404():
    app = _create_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/404")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"] == "not_found"


def test_validation_error_returns_400():
    app = _create_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/400")
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"] == "validation_error"


def test_request_id_header():
    app = _create_test_app()
    client = TestClient(app)
    resp = client.get("/ok")
    assert "x-request-id" in resp.headers
    assert len(resp.headers["x-request-id"]) >= 20
