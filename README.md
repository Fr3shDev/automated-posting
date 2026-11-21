# Automated Multi-Platform Posting System

A FastAPI service that validates a short message containing one call-to-action (CTA) link and publishes it to **6 third-party platforms** through their official APIs: Telegram, Discord, Mastodon, Bluesky, GitHub Gist and DEV Community.

Each platform is handled independently and concurrently. If one platform fails, the others still post, and the response reports the result of every platform.

## Features

- `POST /posting` endpoint on port 4000, with interactive docs at `/docs`
- Input validation: 200 characters max, exactly one CTA link, valid `http(s)` URL with a real domain
- Clear `422` validation errors in a consistent format
- Platform selection handled internally (all configured integrations are used)
- Concurrent posting with `asyncio.gather` and a shared `httpx.AsyncClient`
- Per-platform error isolation: auth errors, API errors, timeouts, network errors and unexpected bugs become a `failed` row instead of crashing the request
- Public-access check for each published post
- Credentials loaded from environment variables / `.env` (never committed)
- Automated tests with fake platforms (no network needed)

## Platforms

| Platform | API used | Credentials | Public access |
|---|---|---|---|
| Telegram | [Bot API `sendMessage`](https://core.telegram.org/bots/api#sendmessage) | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Yes for public channels (`@username`) |
| Discord | [Execute Webhook](https://discord.com/developers/docs/resources/webhook#execute-webhook) | `DISCORD_WEBHOOK_URL` | No (server members only) |
| Mastodon | [`POST /api/v1/statuses`](https://docs.joinmastodon.org/methods/statuses/#create) | `MASTODON_INSTANCE_URL`, `MASTODON_ACCESS_TOKEN` | Checked over HTTP |
| Bluesky | [AT Protocol `createRecord`](https://docs.bsky.app/docs/advanced-guides/posts) | `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` | Checked over HTTP |
| GitHub Gist | [Create a gist](https://docs.github.com/en/rest/gists/gists#create-a-gist) | `GITHUB_TOKEN` (scope: `gist`) | Checked over HTTP |
| DEV Community | [Forem `createArticle`](https://developers.forem.com/api/v1#tag/articles/operation/createArticle) | `DEVTO_API_KEY` | Checked over HTTP |

"Checked over HTTP" means the service requests the post URL anonymously after publishing; a status below 400 means it is publicly accessible.

## Project structure

```text
automated-posting/
├── app/
│   ├── main.py                  # FastAPI app, /posting endpoint, validation error format
│   ├── schemas.py               # Pydantic request/response models + validation rules
│   ├── config.py                # Settings loaded from environment variables / .env
│   ├── platforms/
│   │   ├── __init__.py          # List of integrations (platform selection)
│   │   ├── base.py              # Platform base class, PlatformError, response checking
│   │   ├── telegram.py
│   │   ├── discord.py
│   │   ├── mastodon.py
│   │   ├── bluesky.py
│   │   ├── github_gist.py
│   │   └── devto.py
│   └── services/
│       └── posting_service.py   # Concurrent posting with per-platform error isolation
├── tests/
│   └── test_posting.py
├── docs/
│   └── sample-run.md            # Recorded requests, responses and server logs
├── .env.example
├── requirements.txt
└── README.md
```

## Setup

Requirements: Python 3.10 or newer.

```bash
git clone <this repository URL>
cd automated-posting

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # then fill in the credentials you have
```

Platforms left empty in `.env` are reported as `Not configured` and the rest still work.

### Getting credentials

- **Telegram**: message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token. Create a public channel, add the bot as an admin, and set `TELEGRAM_CHAT_ID=@your_channel`.
- **Discord**: in your server, Channel settings > Integrations > Webhooks > New Webhook > Copy Webhook URL.
- **Mastodon**: Preferences > Development > New application, scope `write:statuses`, copy "Your access token".
- **Bluesky**: Settings > Privacy and security > App passwords > Add app password. Use your handle, e.g. `name.bsky.social`.
- **GitHub Gist**: Settings > Developer settings > Personal access tokens (classic) > Generate, scope `gist` only.
- **DEV Community**: [dev.to/settings/extensions](https://dev.to/settings/extensions) > Generate API key.

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Open the interactive API documentation at <http://localhost:4000/docs>.

## Usage

### Request

```bash
curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Check out our latest business platform and grow your online visibility. https://example.com"}'
```

### Response (200)

`success` is `true` when at least one platform published the message. Dates and times are in UTC. The values below show the shape of the response; real results are in [docs/sample-run.md](docs/sample-run.md).

```json
{
  "success": true,
  "results": [
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@example/113512345678901234",
      "public_access": true,
      "date": "2026-11-21",
      "time": "14:10:03",
      "error": null
    },
    {
      "platform": "GitHub Gist",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "HTTP 401: Bad credentials"
    }
  ]
}
```

### Validation error (422)

```json
{
  "success": false,
  "errors": [
    { "field": "message", "message": "Message must contain exactly one CTA link (found 2)." }
  ]
}
```

| Rule | Example of rejected input |
|---|---|
| Not empty | `"   "` |
| Max 200 characters | a 215-character message |
| Exactly one link | no link, or two links |
| Link must use `http://` or `https://` | `www.example.com` |
| Valid URL with a real domain | `https://localhost`, `https://exa$mple.com` |

Recorded requests, responses and server logs are in [docs/sample-run.md](docs/sample-run.md).

## Tests

```bash
pytest
```

The tests replace the real platforms with fake ones through FastAPI's `dependency_overrides`, so they run offline. They cover every validation rule, the 200-character boundary, isolation of API errors, crashes and missing configuration, the overall `success` flag, and the Bluesky byte-offset link facet.

## Design decisions

- **One class per platform** behind a common `Platform` base class. Adding a platform means writing one `publish()` method and adding the class to `PLATFORM_CLASSES`.
- **Concurrency**: all platforms are called at the same time, so the response takes as long as the slowest platform, not the sum of all of them.
- **Errors never escape a platform**: `post_to_one()` turns every exception into a `failed` result, so one broken integration cannot affect the others.
- **Secrets stay out of logs**: the `httpx` request logger is set to WARNING because the Telegram API URL contains the bot token.
- **Status code**: validation problems return `422`; a valid request returns `200` with per-platform results, even if some platforms failed.

## Security

No credentials are committed. `.env` is listed in `.gitignore`; `.env.example` only contains empty placeholders. Use app passwords or narrowly scoped tokens (for example the GitHub `gist` scope only).
