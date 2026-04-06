"""Middleware — CORS, error handling, request IDs, lifecycle hooks."""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger("atlas.server")


# --- Custom exceptions ---

class AtlasNotFoundError(Exception):
    """Raised when a resource is not found."""
    def __init__(self, detail: str = "Resource not found"):
        self.detail = detail


class AtlasValidationError(Exception):
    """Raised for invalid input."""
    def __init__(self, detail: str = "Invalid input"):
        self.detail = detail


class AtlasErrorHandler:
    """Unified error handler producing consistent JSON error responses."""

    @staticmethod
    async def not_found_handler(request: Request, exc: AtlasNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "detail": exc.detail},
        )

    @staticmethod
    async def validation_handler(request: Request, exc: AtlasValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"error": "validation_error", "detail": exc.detail},
        )

    @staticmethod
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "detail": str(exc)},
        )


def add_middleware(app: FastAPI) -> None:
    """Register all middleware on a FastAPI app instance."""

    # CORS — permissive for local development, tighten for ARA
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    app.add_exception_handler(AtlasNotFoundError, AtlasErrorHandler.not_found_handler)
    app.add_exception_handler(AtlasValidationError, AtlasErrorHandler.validation_handler)
    app.add_exception_handler(Exception, AtlasErrorHandler.unhandled_handler)

    # Request ID + timing middleware
    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = str(uuid.uuid4())
        start = time.monotonic()

        response = await call_next(request)

        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        response.headers["x-request-id"] = request_id
        response.headers["x-response-time-ms"] = str(elapsed_ms)

        logger.info(
            "%s %s %s %sms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
