"""Posts one message to every platform at the same time, isolating each platform's failures."""

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.platforms.base import Platform, PlatformError
from app.schemas import PlatformResult

logger = logging.getLogger(__name__)


async def post_to_all(platforms: list[Platform], message: str, link: str, timeout: float) -> list[PlatformResult]:
    """Post to all platforms concurrently and return one result per platform, in the same order."""
    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": "automated-posting/1.0"}) as client:
        return list(await asyncio.gather(*(post_to_one(p, client, message, link) for p in platforms)))


async def post_to_one(platform: Platform, client: httpx.AsyncClient, message: str, link: str) -> PlatformResult:
    """Never raises: any problem becomes a 'failed' result so the other platforms carry on."""
    missing = platform.missing_settings()
    if missing:
        return _failed(platform, f"Not configured: set {', '.join(missing)} in .env")

    try:
        post = await platform.publish(client, message, link)
    except PlatformError as exc:
        return _failed(platform, str(exc))
    except httpx.TimeoutException:
        return _failed(platform, "Request timed out")
    except httpx.HTTPError as exc:
        return _failed(platform, f"Network error: {type(exc).__name__}")
    except Exception as exc:  # A bug or an unexpected API response must not stop the other platforms.
        logger.exception("Unexpected error while posting to %s", platform.name)
        return _failed(platform, f"Unexpected error: {type(exc).__name__}: {exc}")

    posted_at = datetime.now(timezone.utc)
    public = post.public if post.public is not None else await platform.is_public(client, post.url)

    logger.info("%s: posted %s (public=%s)", platform.name, post.url, public)
    return PlatformResult(
        platform=platform.name,
        status="success",
        posted_url=post.url,
        public_access=public,
        date=posted_at.strftime("%Y-%m-%d"),
        time=posted_at.strftime("%H:%M:%S"),
        error=None,
    )


def _failed(platform: Platform, error: str) -> PlatformResult:
    logger.warning("%s: failed - %s", platform.name, error)
    return PlatformResult(platform=platform.name, status="failed", error=error)
