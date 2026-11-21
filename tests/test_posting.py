"""Tests for POST /posting. No real platform is contacted: fake platforms stand in for them."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app, get_platforms
from app.platforms.base import Platform, PlatformError, PublishedPost
from app.platforms.bluesky import link_facet
from app.platforms.devto import make_title

VALID_MESSAGE = "Check out our latest business platform and grow your online visibility. https://example.com"


# ---------- fake platforms ----------

class FakeSuccess(Platform):
    name = "Fake Success"

    async def publish(self, client, message, link):
        return PublishedPost(url="https://fake.example/post/1", public=True)


class FakeApiError(Platform):
    name = "Fake API Error"

    async def publish(self, client, message, link):
        raise PlatformError("HTTP 401: Authentication failed")


class FakeCrash(Platform):
    name = "Fake Crash"

    async def publish(self, client, message, link):
        raise RuntimeError("something broke")


class FakeNotConfigured(Platform):
    name = "Fake Not Configured"
    required_settings = ("github_token",)

    async def publish(self, client, message, link):  # pragma: no cover - never reached
        raise AssertionError("should not be called")


def use_platforms(*classes):
    settings = Settings(_env_file=None, github_token=None)
    app.dependency_overrides[get_platforms] = lambda: [cls(settings) for cls in classes]


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------- validation ----------

def test_valid_message_is_posted(client):
    use_platforms(FakeSuccess)
    response = client.post("/posting", json={"message": VALID_MESSAGE})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    result = body["results"][0]
    assert result["platform"] == "Fake Success"
    assert result["status"] == "success"
    assert result["posted_url"] == "https://fake.example/post/1"
    assert result["public_access"] is True
    assert result["date"] and result["time"]
    assert result["error"] is None


@pytest.mark.parametrize(
    "message, expected_error",
    [
        ("A" * 190 + " https://example.com", "must not exceed 200 characters"),
        ("No link in this message at all", "exactly one CTA link (found 0)"),
        ("Two links https://a.com and https://b.com", "exactly one CTA link (found 2)"),
        ("Visit www.example.com today", "must start with http:// or https://"),
        ("Visit https://localhost now", "full domain name"),
        ("Visit https://exa$mple.com now", "not a valid URL"),
        ("   ", "must not be empty"),
    ],
)
def test_invalid_messages_are_rejected(client, message, expected_error):
    use_platforms(FakeSuccess)
    response = client.post("/posting", json={"message": message})

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["errors"][0]["field"] == "message"
    assert expected_error in body["errors"][0]["message"]


def test_exactly_200_characters_is_allowed(client):
    use_platforms(FakeSuccess)
    link = " https://example.com"
    message = "A" * (200 - len(link)) + link
    assert len(message) == 200

    assert client.post("/posting", json={"message": message}).status_code == 200


def test_trailing_punctuation_is_not_part_of_the_link(client):
    use_platforms(FakeSuccess)
    response = client.post("/posting", json={"message": "Read more at https://example.com/page."})
    assert response.status_code == 200


def test_missing_message_field(client):
    response = client.post("/posting", json={})
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "message"


def test_message_must_be_text(client):
    response = client.post("/posting", json={"message": 123})
    assert response.status_code == 422


# ---------- one failure must not stop the others ----------

def test_failures_are_isolated_per_platform(client):
    use_platforms(FakeApiError, FakeSuccess, FakeCrash, FakeNotConfigured)
    response = client.post("/posting", json={"message": VALID_MESSAGE})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True  # at least one platform worked

    by_name = {r["platform"]: r for r in body["results"]}
    assert by_name["Fake Success"]["status"] == "success"

    assert by_name["Fake API Error"]["status"] == "failed"
    assert by_name["Fake API Error"]["error"] == "HTTP 401: Authentication failed"
    assert by_name["Fake API Error"]["posted_url"] is None
    assert by_name["Fake API Error"]["public_access"] is False

    assert by_name["Fake Crash"]["status"] == "failed"
    assert "RuntimeError" in by_name["Fake Crash"]["error"]

    assert by_name["Fake Not Configured"]["error"] == "Not configured: set GITHUB_TOKEN in .env"


def test_success_is_false_when_every_platform_fails(client):
    use_platforms(FakeApiError, FakeCrash)
    body = client.post("/posting", json={"message": VALID_MESSAGE}).json()
    assert body["success"] is False
    assert all(r["status"] == "failed" for r in body["results"])


def test_real_platforms_without_credentials_report_not_configured(client):
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, **{
        name: None for name in Settings.model_fields if name != "request_timeout"
    })
    body = client.post("/posting", json={"message": VALID_MESSAGE}).json()

    assert len(body["results"]) >= 5
    assert all(r["error"].startswith("Not configured") for r in body["results"])


# ---------- platform helpers ----------

def test_bluesky_link_facet_counts_bytes():
    message = "Café ☕ https://example.com"  # é and ☕ take more than one byte in UTF-8
    facet = link_facet(message, "https://example.com")
    start, end = facet["index"]["byteStart"], facet["index"]["byteEnd"]
    assert message.encode()[start:end] == b"https://example.com"


def test_devto_title_drops_the_link():
    assert make_title("Big news today https://example.com", "https://example.com") == "Big news today"
    assert make_title("https://example.com", "https://example.com") == "Update"
