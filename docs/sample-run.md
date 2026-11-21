# Sample run

Recorded on 2026-11-21 against a local server (`uvicorn app.main:app --port 4000`).

## 1. Requests with no API keys configured

Every platform is reported as **Not configured**, and invalid messages are rejected with **422**.

### Valid message (no API keys configured yet)

```bash
curl -X POST http://localhost:4000/posting -H 'Content-Type: application/json' -d '{"message": "Check out our latest business platform and grow your online visibility. https://example.com"}'
```

```json
{
    "success": false,
    "results": [
        {
            "platform": "Telegram",
            "status": "failed",
            "posted_url": null,
            "public_access": false,
            "date": null,
            "time": null,
            "error": "Not configured: set TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID in .env"
        },
        {
            "platform": "Discord",
            "status": "failed",
            "posted_url": null,
            "public_access": false,
            "date": null,
            "time": null,
            "error": "Not configured: set DISCORD_WEBHOOK_URL in .env"
        },
        {
            "platform": "Mastodon",
            "status": "failed",
            "posted_url": null,
            "public_access": false,
            "date": null,
            "time": null,
            "error": "Not configured: set MASTODON_INSTANCE_URL, MASTODON_ACCESS_TOKEN in .env"
        },
        {
            "platform": "Bluesky",
            "status": "failed",
            "posted_url": null,
            "public_access": false,
            "date": null,
            "time": null,
            "error": "Not configured: set BLUESKY_HANDLE, BLUESKY_APP_PASSWORD in .env"
        },
        {
            "platform": "GitHub Gist",
            "status": "failed",
            "posted_url": null,
            "public_access": false,
            "date": null,
            "time": null,
            "error": "Not configured: set GITHUB_TOKEN in .env"
        },
        {
            "platform": "DEV Community",
            "status": "failed",
            "posted_url": null,
            "public_access": false,
            "date": null,
            "time": null,
            "error": "Not configured: set DEVTO_API_KEY in .env"
        }
    ]
}
```

### Message over 200 characters

```bash
curl -X POST http://localhost:4000/posting -H 'Content-Type: application/json' -d '{"message": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA https://example.com"}'
```

```json
{
    "success": false,
    "errors": [
        {
            "field": "message",
            "message": "Message must not exceed 200 characters (got 215)."
        }
    ]
}
```

### No link

```bash
curl -X POST http://localhost:4000/posting -H 'Content-Type: application/json' -d '{"message": "Check out our latest business platform."}'
```

```json
{
    "success": false,
    "errors": [
        {
            "field": "message",
            "message": "Message must contain exactly one CTA link (found 0)."
        }
    ]
}
```

### Two links

```bash
curl -X POST http://localhost:4000/posting -H 'Content-Type: application/json' -d '{"message": "Visit https://example.com and https://example.org"}'
```

```json
{
    "success": false,
    "errors": [
        {
            "field": "message",
            "message": "Message must contain exactly one CTA link (found 2)."
        }
    ]
}
```

### Invalid URL

```bash
curl -X POST http://localhost:4000/posting -H 'Content-Type: application/json' -d '{"message": "Visit https://localhost now"}'
```

```json
{
    "success": false,
    "errors": [
        {
            "field": "message",
            "message": "The CTA link must use a full domain name, e.g. https://example.com (got 'https://localhost')."
        }
    ]
}
```

## 2. Real platform APIs answering with invalid credentials

The server was started with deliberately wrong keys for Mastodon, GitHub and DEV Community. The real APIs refused them, and each failure was reported separately while the request still completed:

```json
{
    "success": false,
    "results": [
        {
            "platform": "Telegram",
            "status": "failed",
            "posted_url": null,
            "public_access": false,
            "date": null,
            "time": null,
            "error": "Not configured: set TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID in .env"
        },
        {
            "platform": "Discord",
            "status": "failed",
            "posted_url": null,
            "public_access": false,
            "date": null,
            "time": null,
            "error": "Not configured: set DISCORD_WEBHOOK_URL in .env"
        },
        {
            "platform": "Mastodon",
            "status": "failed",
            "posted_url": null,
            "public_access": false,
            "date": null,
            "time": null,
            "error": "HTTP 401: The access token is invalid"
        },
        {
            "platform": "Bluesky",
            "status": "failed",
            "posted_url": null,
            "public_access": false,
            "date": null,
            "time": null,
            "error": "Not configured: set BLUESKY_HANDLE, BLUESKY_APP_PASSWORD in .env"
        },
        {
            "platform": "GitHub Gist",
            "status": "failed",
            "posted_url": null,
            "public_access": false,
            "date": null,
            "time": null,
            "error": "HTTP 401: Bad credentials"
        },
        {
            "platform": "DEV Community",
            "status": "failed",
            "posted_url": null,
            "public_access": false,
            "date": null,
            "time": null,
            "error": "HTTP 401: unauthorized"
        }
    ]
}
```

### Server log

```text
INFO:     Started server process [5011]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:4001 (Press CTRL+C to quit)
2026-11-21 14:07:04,832 WARNING app.services.posting_service: Telegram: failed - Not configured: set TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID in .env
2026-11-21 14:07:04,832 WARNING app.services.posting_service: Discord: failed - Not configured: set DISCORD_WEBHOOK_URL in .env
2026-11-21 14:07:04,833 WARNING app.services.posting_service: Bluesky: failed - Not configured: set BLUESKY_HANDLE, BLUESKY_APP_PASSWORD in .env
2026-11-21 14:07:07,456 WARNING app.services.posting_service: Mastodon: failed - HTTP 401: The access token is invalid
2026-11-21 14:07:07,456 WARNING app.services.posting_service: GitHub Gist: failed - HTTP 401: Bad credentials
2026-11-21 14:07:07,776 WARNING app.services.posting_service: DEV Community: failed - HTTP 401: unauthorized
INFO:     127.0.0.1:57188 - "POST /posting HTTP/1.1" 200 OK
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [5011]
```
