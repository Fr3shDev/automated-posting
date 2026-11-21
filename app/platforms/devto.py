"""DEV Community (Forem) API: https://developers.forem.com/api/v1#tag/articles/operation/createArticle"""

import httpx

from app.platforms.base import Platform, PublishedPost, check_response


def make_title(message: str, link: str) -> str:
    """dev.to articles need a title: use the message text without the link, shortened."""
    text = " ".join(message.replace(link, "").split())
    if len(text) > 80:
        text = text[:77].rstrip() + "..."
    return text or "Update"


class DevToPlatform(Platform):
    name = "DEV Community"
    required_settings = ("devto_api_key",)

    async def publish(self, client: httpx.AsyncClient, message: str, link: str) -> PublishedPost:
        response = await client.post(
            "https://dev.to/api/articles",
            headers={"api-key": self.settings.devto_api_key, "Accept": "application/vnd.forem.api-v1+json"},
            json={"article": {"title": make_title(message, link), "body_markdown": message, "published": True}},
        )
        article = check_response(response)
        return PublishedPost(url=article["url"])
