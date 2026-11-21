"""FastAPI application: the POST /posting endpoint.

Run with:
    uvicorn app.main:app --host 0.0.0.0 --port 4000
"""

import logging

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.platforms import build_platforms
from app.platforms.base import Platform
from app.schemas import PostRequest, PostResponse, ValidationErrorResponse
from app.services.posting_service import post_to_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
# httpx logs every request URL at INFO level; the Telegram URL contains the bot token, so keep it quiet.
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(
    title="Automated Multi-Platform Posting System",
    version="1.0.0",
    description="Validates a short message with one CTA link and publishes it to several platforms through their APIs.",
)


def get_platforms(settings: Settings = Depends(get_settings)) -> list[Platform]:
    """Platform selection is internal: every integration is used (unconfigured ones report it)."""
    return build_platforms(settings)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Turn FastAPI's default validation output into short, readable messages."""
    errors = []
    for error in exc.errors():
        field = ".".join(str(part) for part in error["loc"] if part != "body") or "body"
        original = error.get("ctx", {}).get("error")  # our own ValueError, without the "Value error," prefix
        errors.append({"field": field, "message": str(original) if original else error["msg"]})
    return JSONResponse(status_code=422, content={"success": False, "errors": errors})


@app.get("/", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "docs": "/docs"}


@app.post(
    "/posting",
    response_model=PostResponse,
    responses={422: {"model": ValidationErrorResponse, "description": "Invalid message"}},
    tags=["posting"],
)
async def create_posting(
    request: PostRequest,
    platforms: list[Platform] = Depends(get_platforms),
    settings: Settings = Depends(get_settings),
) -> PostResponse:
    results = await post_to_all(platforms, request.message, request.link, settings.request_timeout)
    return PostResponse(success=any(r.status == "success" for r in results), results=results)
