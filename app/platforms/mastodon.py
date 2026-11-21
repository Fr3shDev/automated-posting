"""Mastodon API: https://docs.joinmastodon.org/methods/statuses/#create"""

import uuid

import httpx

from app.platforms.base import Platform, PublishedPost, check_response


class MastodonPlatform(Platform):
    name = "Mastodon"
    required_settings = ("mastodon_instance_url", "mastodon_access_token")

    async def publish(self, client: httpx.AsyncClient, message: str, link: str) -> PublishedPost:
        base_url = self.settings.mastodon_instance_url.rstrip("/")
        response = await client.post(
            f"{base_url}/api/v1/statuses",
            headers={
                "Authorization": f"Bearer {self.settings.mastodon_access_token}",
                # Protects against a duplicate post if the request is retried.
                "Idempotency-Key": str(uuid.uuid4()),
            },
            data={"status": message, "visibility": "public"},
        )
        status = check_response(response)
        return PublishedPost(url=status["url"])
