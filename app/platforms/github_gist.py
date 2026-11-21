"""GitHub Gists API: https://docs.github.com/en/rest/gists/gists#create-a-gist"""

import httpx

from app.platforms.base import Platform, PublishedPost, check_response


class GitHubGistPlatform(Platform):
    name = "GitHub Gist"
    required_settings = ("github_token",)

    async def publish(self, client: httpx.AsyncClient, message: str, link: str) -> PublishedPost:
        response = await client.post(
            "https://api.github.com/gists",
            headers={
                "Authorization": f"Bearer {self.settings.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={
                "description": "Automated post",
                "public": True,
                "files": {"message.md": {"content": message}},
            },
        )
        gist = check_response(response)
        return PublishedPost(url=gist["html_url"])
