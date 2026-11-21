"""Application settings.

Values are read from environment variables, or from a local `.env` file.
Every credential is optional: a platform whose settings are missing is skipped
and reported as "Not configured" instead of crashing the app.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Seconds to wait for each platform API call
    request_timeout: float = 15.0

    # Telegram: a bot that posts into a channel
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None  # e.g. "@my_public_channel"

    # Discord: a channel webhook URL
    discord_webhook_url: str | None = None

    # Mastodon
    mastodon_instance_url: str | None = None  # e.g. "https://mastodon.social"
    mastodon_access_token: str | None = None

    # Bluesky
    bluesky_handle: str | None = None  # e.g. "yourname.bsky.social"
    bluesky_app_password: str | None = None

    # GitHub Gist
    github_token: str | None = None

    # DEV Community (dev.to)
    devto_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Load the settings once and reuse them for every request."""
    return Settings()
