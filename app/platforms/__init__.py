"""All platform integrations. The app decides internally which platforms to post to."""

from app.config import Settings
from app.platforms.base import Platform
from app.platforms.bluesky import BlueskyPlatform
from app.platforms.devto import DevToPlatform
from app.platforms.discord import DiscordPlatform
from app.platforms.github_gist import GitHubGistPlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.telegram import TelegramPlatform

PLATFORM_CLASSES: list[type[Platform]] = [
    TelegramPlatform,
    DiscordPlatform,
    MastodonPlatform,
    BlueskyPlatform,
    GitHubGistPlatform,
    DevToPlatform,
]


def build_platforms(settings: Settings) -> list[Platform]:
    return [platform_class(settings) for platform_class in PLATFORM_CLASSES]
