"""Request and response models (Pydantic), including the input validation rules."""

import re
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, TypeAdapter, ValidationError, field_validator

MAX_MESSAGE_LENGTH = 200

# Anything that looks like a link: starts with http://, https:// or www. and runs until whitespace.
LINK_PATTERN = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)

# Punctuation that usually ends a sentence rather than belonging to the URL ("... https://x.com.").
TRAILING_PUNCTUATION = ".,!?;:)]}'\""

# Domain names: labels of letters, digits and hyphens, ending in a top-level domain such as .com.
# (Pydantic turns international names into "xn--" form first, so they match too.)
DOMAIN_PATTERN = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:[a-z]{2,63}|xn--[a-z0-9-]{1,59})")

_url_validator = TypeAdapter(HttpUrl)


def find_links(text: str) -> list[str]:
    """Return every link-like string in the text, without trailing punctuation."""
    return [match.rstrip(TRAILING_PUNCTUATION) for match in LINK_PATTERN.findall(text)]


class PostRequest(BaseModel):
    message: str = Field(
        ...,
        description=f"Text to publish. Max {MAX_MESSAGE_LENGTH} characters, exactly one http(s) link.",
        examples=["Check out our latest business platform and grow your online visibility. https://example.com"],
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Message must not be empty.")

        if len(value) > MAX_MESSAGE_LENGTH:
            raise ValueError(f"Message must not exceed {MAX_MESSAGE_LENGTH} characters (got {len(value)}).")

        links = find_links(value)
        if len(links) != 1:
            raise ValueError(f"Message must contain exactly one CTA link (found {len(links)}).")

        link = links[0]
        if not link.lower().startswith(("http://", "https://")):
            raise ValueError(f"The CTA link must start with http:// or https:// (got '{link}').")

        try:
            url = _url_validator.validate_python(link)
        except ValidationError:
            raise ValueError(f"The CTA link is not a valid URL: '{link}'.") from None

        # A public call-to-action link needs a real domain such as example.com (not "localhost").
        if not url.host or "." not in url.host:
            raise ValueError(f"The CTA link must use a full domain name, e.g. https://example.com (got '{link}').")
        if not DOMAIN_PATTERN.fullmatch(url.host):
            raise ValueError(f"The CTA link is not a valid URL: '{link}'.")

        return value

    @property
    def link(self) -> str:
        """The single CTA link found in the (already validated) message."""
        return find_links(self.message)[0]


class PlatformResult(BaseModel):
    platform: str
    status: Literal["success", "failed"]
    posted_url: str | None = None
    public_access: bool = False
    date: str | None = Field(None, description="Posting date in UTC, YYYY-MM-DD")
    time: str | None = Field(None, description="Posting time in UTC, HH:MM:SS")
    error: str | None = None


class PostResponse(BaseModel):
    success: bool = Field(..., description="True when at least one platform published the message.")
    results: list[PlatformResult]


class FieldError(BaseModel):
    field: str
    message: str


class ValidationErrorResponse(BaseModel):
    success: Literal[False] = False
    errors: list[FieldError]
