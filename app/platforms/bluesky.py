"""Bluesky (AT Protocol): https://docs.bsky.app/docs/advanced-guides/posts"""

from datetime import datetime, timezone

import httpx

from app.platforms.base import Platform, PublishedPost, check_response

API = "https://bsky.social/xrpc"


def link_facet(message: str, link: str) -> dict:
    """Mark the link as clickable. Bluesky counts positions in UTF-8 bytes, not characters."""
    text_bytes = message.encode("utf-8")
    link_bytes = link.encode("utf-8")
    start = text_bytes.find(link_bytes)
    return {
        "index": {"byteStart": start, "byteEnd": start + len(link_bytes)},
        "features": [{"$type": "app.bsky.richtext.facet#link", "uri": link}],
    }


class BlueskyPlatform(Platform):
    name = "Bluesky"
    required_settings = ("bluesky_handle", "bluesky_app_password")

    async def publish(self, client: httpx.AsyncClient, message: str, link: str) -> PublishedPost:
        # 1. Log in with the app password to get a short-lived access token.
        session = check_response(
            await client.post(
                f"{API}/com.atproto.server.createSession",
                json={"identifier": self.settings.bluesky_handle, "password": self.settings.bluesky_app_password},
            )
        )

        # 2. Create the post record.
        record = {
            "$type": "app.bsky.feed.post",
            "text": message,
            "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "facets": [link_facet(message, link)],
        }
        created = check_response(
            await client.post(
                f"{API}/com.atproto.repo.createRecord",
                headers={"Authorization": f"Bearer {session['accessJwt']}"},
                json={"repo": session["did"], "collection": "app.bsky.feed.post", "record": record},
            )
        )

        # The record URI ends with the post id ("rkey"), which is also used in the web URL.
        post_id = created["uri"].rsplit("/", 1)[-1]
        return PublishedPost(url=f"https://bsky.app/profile/{session['handle']}/post/{post_id}")
