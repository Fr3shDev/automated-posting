"""The shared contract that every platform integration follows."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.config import Settings


class PlatformError(Exception):
    """A platform API refused the post. The message is safe to show to the API caller."""


@dataclass
class PublishedPost:
    url: str
    # True/False when the platform itself tells us; None means "check the URL over HTTP".
    public: bool | None = None


class Platform(ABC):
    """Base class for one third-party platform.

    Subclasses set `name` and `required_settings` and implement `publish`.
    """

    name: str = "Unnamed platform"
    # Names of the Settings fields this platform needs, e.g. ("github_token",)
    required_settings: tuple[str, ...] = ()

    def __init__(self, settings: Settings):
        self.settings = settings

    def missing_settings(self) -> list[str]:
        """Environment variable names that still need a value."""
        return [name.upper() for name in self.required_settings if not getattr(self.settings, name, None)]

    @abstractmethod
    async def publish(self, client: httpx.AsyncClient, message: str, link: str) -> PublishedPost:
        """Publish the message and return where it was posted. Raise PlatformError on API errors."""

    async def is_public(self, client: httpx.AsyncClient, url: str) -> bool:
        """Default check: can an anonymous visitor open the post URL?"""
        try:
            response = await client.get(url, follow_redirects=True)
        except httpx.HTTPError:
            return False
        return response.status_code < 400


def check_response(response: httpx.Response) -> dict:
    """Return the JSON body of a successful response, or raise PlatformError with the API's reason."""
    if response.is_success:
        return response.json() if response.content else {}

    detail = response.text[:200] or response.reason_phrase
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        for key in ("description", "message", "error_description", "error"):
            if body.get(key):
                detail = str(body[key])
                break

    raise PlatformError(f"HTTP {response.status_code}: {detail}")
