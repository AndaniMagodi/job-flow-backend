"""Greenhouse public job boards.

Depth-first source: no API key, no rate limit worth worrying about, and — unlike
an aggregator — the *full* job description. The trade-off is coverage: it only
sees companies you list, and SA companies on Greenhouse skew toward tech.

These endpoints are the same ones that render each company's own careers page,
so they are public by design rather than scraped.
"""

from __future__ import annotations

import html
import re
from datetime import datetime

import httpx

from app.core.config import settings
from app.jobs.sources.base import (
    JobSource,
    JobSourceError,
    NormalisedJob,
    normalise_province,
)

BOARD_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"

# Board tokens for SA employers, as `token:Display Name`. Override with
# GREENHOUSE_BOARDS in .env; a board that 404s is skipped, not fatal, so a
# company leaving Greenhouse never breaks a sync.
DEFAULT_BOARDS = "luno:Luno,ozow:Ozow,entersekt:Entersekt,stitch:Stitch"

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(content: str | None) -> str | None:
    if not content:
        return None

    text = html.unescape(content)
    text = re.sub(r"<(br|/p|/li|/div|/h[1-6])\s*/?>", "\n", text, flags=re.I)
    text = _TAG_RE.sub("", text)
    # Entities can survive one pass when the source double-encoded them.
    text = html.unescape(text)

    # Non-breaking spaces come through as \xa0 and would otherwise leave
    # "blank" lines that are not actually empty, so normalise them first.
    text = text.replace("\xa0", " ")
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    return re.sub(r"\n{3,}", "\n\n", text).strip()


class GreenhouseSource(JobSource):
    name = "greenhouse"
    # Listings link to the employer's own posting, which is where they want
    # applications to land anyway.
    requires_attribution = True

    def __init__(self, boards: str | None = None):
        raw = boards or settings.greenhouse_boards or DEFAULT_BOARDS
        self.boards: list[tuple[str, str]] = []
        for entry in raw.split(","):
            entry = entry.strip()
            if not entry:
                continue
            token, _, display = entry.partition(":")
            self.boards.append((token.strip(), (display or token).strip()))

    def is_configured(self) -> bool:
        return bool(self.boards)

    def fetch(self, query: str | None = None, limit: int = 50) -> list[NormalisedJob]:
        if not self.is_configured():
            raise JobSourceError("No Greenhouse boards configured")

        jobs: list[NormalisedJob] = []
        for token, display_name in self.boards:
            if len(jobs) >= limit:
                break
            for raw in self._fetch_board(token):
                normalised = self._normalise(raw, display_name)
                if normalised is None:
                    continue
                if query and query.lower() not in normalised.title.lower():
                    continue
                jobs.append(normalised)
                if len(jobs) >= limit:
                    break

        return jobs

    @staticmethod
    def _fetch_board(token: str) -> list[dict]:
        try:
            response = httpx.get(
                BOARD_URL.format(token=token),
                params={"content": "true"},
                timeout=20.0,
            )
            # A company that has left Greenhouse should not fail the whole sync.
            if response.status_code == 404:
                return []
            response.raise_for_status()
            return response.json().get("jobs") or []
        except httpx.HTTPError:
            return []
        except ValueError:
            return []

    @staticmethod
    def _normalise(raw: dict, company: str) -> NormalisedJob | None:
        location = (raw.get("location") or {}).get("name")
        province = normalise_province(location)

        # These boards are global; keep only what is actually in South Africa.
        if province is None and not _mentions_south_africa(location):
            return None

        posted_at = None
        if updated := raw.get("updated_at") or raw.get("first_published"):
            try:
                posted_at = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            except ValueError:
                posted_at = None

        return NormalisedJob(
            source=GreenhouseSource.name,
            source_id=str(raw.get("id")),
            apply_url=raw.get("absolute_url", ""),
            title=(raw.get("title") or "").strip(),
            company=company,
            description=_strip_html(raw.get("content")),
            description_is_truncated=False,
            location=location,
            province=province,
            posted_at=posted_at,
            salary_period=None,
        )


def _mentions_south_africa(location: str | None) -> bool:
    if not location:
        return False
    lowered = location.lower()
    return "south africa" in lowered or lowered.strip() in {"za", "rsa"}
