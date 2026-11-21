"""Discord webhooks: https://discord.com/developers/docs/resources/webhook#execute-webhook"""

import httpx

from app.platforms.base import Platform, PublishedPost, check_response


class DiscordPlatform(Platform):
    name = "Discord"
    required_settings = ("discord_webhook_url",)

    async def publish(self, client: httpx.AsyncClient, message: str, link: str) -> PublishedPost:
        webhook_url = self.settings.discord_webhook_url

        # wait=true makes Discord return the created message (so we get its id).
        sent = check_response(await client.post(webhook_url, params={"wait": "true"}, json={"content": message}))

        # The webhook's own details tell us which server (guild) it belongs to.
        webhook = check_response(await client.get(webhook_url))
        url = f"https://discord.com/channels/{webhook['guild_id']}/{sent['channel_id']}/{sent['id']}"

        # Discord messages are only visible to members of the server, never to anonymous visitors.
        return PublishedPost(url=url, public=False)
