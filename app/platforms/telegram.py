"""Telegram Bot API: https://core.telegram.org/bots/api#sendmessage"""

import httpx

from app.platforms.base import Platform, PublishedPost, check_response


class TelegramPlatform(Platform):
    name = "Telegram"
    required_settings = ("telegram_bot_token", "telegram_chat_id")

    async def publish(self, client: httpx.AsyncClient, message: str, link: str) -> PublishedPost:
        response = await client.post(
            f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage",
            json={"chat_id": self.settings.telegram_chat_id, "text": message},
        )
        sent = check_response(response)["result"]
        chat = sent["chat"]

        # Public channels have a username and a t.me/<username>/<id> link anyone can open.
        if chat.get("username"):
            return PublishedPost(url=f"https://t.me/{chat['username']}/{sent['message_id']}", public=True)

        # Private chats only have an internal link that works for members.
        internal_id = str(chat["id"]).removeprefix("-100")
        return PublishedPost(url=f"https://t.me/c/{internal_id}/{sent['message_id']}", public=False)
