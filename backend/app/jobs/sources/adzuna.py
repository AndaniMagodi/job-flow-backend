"""Adzuna's South Africa endpoint.

Breadth-first source: it covers most SA boards, but descriptions come back
truncated and their terms require sending the applicant to `redirect_url`
rather than hosting the apply flow — hence `requires_attribution`.

Free credentials: https://developer.adzuna.com/ (app_id + app_key, ~1k calls/mo).
"""

from __future__ import annotations

from datetime import datetime

import httpx

from app.core.config import settings
from app.jobs.sources.base import JobSource, JobSourceError, NormalisedJob

BASE_URL = "https://api.adzuna.com/v1/api/jobs/za/search"
# Adzuna quotes South African salaries annually.
SALARY_PERIOD = "year"
MAX_RESULTS_PER_PAGE = 50

# Adzuna labels every sector "<Something> Jobs" and uses its own vocabulary.
# Map it onto the same sector names the other sources use, otherwise the filter
# dropdown lists "IT" and "IT Jobs" as two separate options.
_CATEGORY_MAP = {
    "Accounting & Finance Jobs": "Finance",
    "Admin Jobs": "Admin",
    "Charity & Voluntary Jobs": "Non-profit",
    "Consultancy Jobs": "Consulting",
    "Creative & Design Jobs": "Design",
    "Customer Services Jobs": "Support",
    "Domestic help & Cleaning Jobs": "Domestic",
    "Energy, Oil & Gas Jobs": "Energy",
    "Engineering Jobs": "Engineering",
    "Graduate Jobs": "Graduate",
    "HR & Recruitment Jobs": "HR",
    "Healthcare & Nursing Jobs": "Healthcare",
    "Hospitality & Catering Jobs": "Hospitality",
    "IT Jobs": "IT",
    "Legal Jobs": "Legal",
    "Logistics & Warehouse Jobs": "Logistics",
    "Maintenance Jobs": "Maintenance",
    "Manufacturing Jobs": "Manufacturing",
    "PR, Advertising & Marketing Jobs": "Marketing",
    "Property Jobs": "Property",
    "Retail Jobs": "Retail",
    "Sales Jobs": "Sales",
    "Scientific & QA Jobs": "Science",
    "Social work Jobs": "Social work",
    "Teaching Jobs": "Education",
    "Trade & Construction Jobs": "Construction",
    "Travel Jobs": "Travel",
}

# Not real sectors — filtering by them tells a seeker nothing.
_CATEGORY_NOISE = {"Other/General Jobs", "Part time Jobs", "Unknown"}

# Roughly a fifth of Adzuna listings are posted by recruiters without naming the
# employer. "Unknown" reads like a bug, so say what is actually true.
UNDISCLOSED_COMPANY = "Company not disclosed"


def _normalise_category(label: str | None) -> str | None:
    if not label or label in _CATEGORY_NOISE:
        return None
    if label in _CATEGORY_MAP:
        return _CATEGORY_MAP[label]
    # Unmapped sectors still read cleanly without the trailing "Jobs".
    return label.removesuffix(" Jobs").strip() or None


def _normalise_contract(contract_type: str | None, contract_time: str | None) -> str | None:
    """Adzuna splits this across two fields; we store one.

    `contract_time` (full_time/part_time) is the more useful of the two to a
    seeker, so it wins when present.
    """
    if contract_time == "part_time":
        return "Part time"
    if contract_time == "full_time":
        return "Full time"
    if contract_type == "contract":
        return "Contract"
    if contract_type == "permanent":
        return "Full time"
    return None


class AdzunaSource(JobSource):
    name = "adzuna"
    requires_attribution = True

    def __init__(self, app_id: str | None = None, app_key: str | None = None):
        self.app_id = app_id or settings.adzuna_app_id
        self.app_key = app_key or settings.adzuna_app_key

    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_key)

    def fetch(self, query: str | None = None, limit: int = 50) -> list[NormalisedJob]:
        if not self.is_configured():
            raise JobSourceError(
                "Adzuna is not configured — set ADZUNA_APP_ID and ADZUNA_APP_KEY"
            )

        jobs: list[NormalisedJob] = []
        page = 1
        # The free tier is ~1k calls/month, so walk pages only until `limit` is met.
        while len(jobs) < limit:
            params = {
                "app_id": self.app_id,
                "app_key": self.app_key,
                "results_per_page": min(MAX_RESULTS_PER_PAGE, limit - len(jobs)),
                "content-type": "application/json",
            }
            if query:
                params["what"] = query

            try:
                response = httpx.get(f"{BASE_URL}/{page}", params=params, timeout=20.0)
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPError as e:
                raise JobSourceError(f"Adzuna request failed: {e}") from e
            except ValueError as e:
                raise JobSourceError("Adzuna returned invalid JSON") from e

            results = payload.get("results") or []
            if not results:
                break

            jobs.extend(self._normalise(r) for r in results)
            page += 1

        return jobs[:limit]

    @staticmethod
    def _normalise(raw: dict) -> NormalisedJob:
        company = (raw.get("company") or {}).get("display_name") or UNDISCLOSED_COMPANY
        location = (raw.get("location") or {}).get("display_name")
        category = _normalise_category((raw.get("category") or {}).get("label"))

        posted_at = None
        if created := raw.get("created"):
            try:
                posted_at = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except ValueError:
                posted_at = None

        return NormalisedJob(
            source=AdzunaSource.name,
            source_id=str(raw.get("id")),
            apply_url=raw.get("redirect_url", ""),
            title=raw.get("title", "").strip(),
            company=company,
            # Adzuna truncates descriptions; flag it so the UI can say so
            # instead of implying the listing is this short.
            description=raw.get("description"),
            description_is_truncated=True,
            location=location,
            salary_min=raw.get("salary_min"),
            salary_max=raw.get("salary_max"),
            salary_is_predicted=str(raw.get("salary_is_predicted", "0")) == "1",
            salary_period=SALARY_PERIOD,
            category=category,
            contract_type=_normalise_contract(
                raw.get("contract_type"), raw.get("contract_time")
            ),
            posted_at=posted_at,
        )
