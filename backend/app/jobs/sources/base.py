"""Source-agnostic job ingestion.

Every external provider is normalised to `NormalisedJob` before it reaches the
database, so routes and the UI never learn which board a listing came from.
Adding a provider means adding one file here and registering it — nothing else
in the app changes.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

PROVINCES = [
    "Gauteng",
    "Western Cape",
    "KwaZulu-Natal",
    "Eastern Cape",
    "Free State",
    "Limpopo",
    "Mpumalanga",
    "North West",
    "Northern Cape",
]

# Sources spell South African locations freely ("Sandton", "Cape Town, WC",
# "Tshwane"), so we map the common city and metro names onto the nine
# provinces to keep the browse filters stable.
_CITY_TO_PROVINCE = {
    "johannesburg": "Gauteng",
    "joburg": "Gauteng",
    "jhb": "Gauteng",
    "sandton": "Gauteng",
    "rosebank": "Gauteng",
    "randburg": "Gauteng",
    "roodepoort": "Gauteng",
    "midrand": "Gauteng",
    "pretoria": "Gauteng",
    "centurion": "Gauteng",
    "tshwane": "Gauteng",
    "ekurhuleni": "Gauteng",
    "benoni": "Gauteng",
    "boksburg": "Gauteng",
    "kempton park": "Gauteng",
    "soweto": "Gauteng",
    "vanderbijlpark": "Gauteng",
    "cape town": "Western Cape",
    "kaapstad": "Western Cape",
    "cpt": "Western Cape",
    "bellville": "Western Cape",
    "century city": "Western Cape",
    "claremont": "Western Cape",
    "stellenbosch": "Western Cape",
    "paarl": "Western Cape",
    "somerset west": "Western Cape",
    "george": "Western Cape",
    "durban": "KwaZulu-Natal",
    "ethekwini": "KwaZulu-Natal",
    "umhlanga": "KwaZulu-Natal",
    "ballito": "KwaZulu-Natal",
    "pietermaritzburg": "KwaZulu-Natal",
    "richards bay": "KwaZulu-Natal",
    "gqeberha": "Eastern Cape",
    "port elizabeth": "Eastern Cape",
    "east london": "Eastern Cape",
    "makhanda": "Eastern Cape",
    "mthatha": "Eastern Cape",
    "bloemfontein": "Free State",
    "mangaung": "Free State",
    "welkom": "Free State",
    "polokwane": "Limpopo",
    "tzaneen": "Limpopo",
    "thohoyandou": "Limpopo",
    "mbombela": "Mpumalanga",
    "nelspruit": "Mpumalanga",
    "emalahleni": "Mpumalanga",
    "witbank": "Mpumalanga",
    "secunda": "Mpumalanga",
    "rustenburg": "North West",
    "mahikeng": "North West",
    "potchefstroom": "North West",
    "klerksdorp": "North West",
    "kimberley": "Northern Cape",
    "upington": "Northern Cape",
}

_REMOTE_HINTS = ("remote", "work from home", "wfh", "hybrid", "anywhere")

# South African youth employment runs heavily through structured programmes
# rather than ordinary vacancies, and seekers search for them by name. Treating
# them as a first-class type — rather than burying them among "Entry" jobs —
# is the difference between finding one and not.
OPPORTUNITY_TYPES = [
    "Job",
    "Learnership",
    "Internship",
    "Graduate programme",
    "Apprenticeship",
]

# Ordered: the first match wins, so more specific programmes come first.
# These are regexes rather than substrings because word boundaries matter —
# a plain "intern" search would tag every "Internal Auditor" as an internship.
_OPPORTUNITY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "Learnership",
        re.compile(
            r"\blearnerships?\b|\byes\s*4?\s*youth\b|\byes\s+programme\b"
            r"|\byouth\s+employment\s+service\b|\bseta\s+programme\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Graduate programme",
        re.compile(
            r"\bgraduate\s+(?:programme|program|trainee|development)\b"
            r"|\bgrad\s+programme\b|\btrainee\s+(?:programme|program)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Internship",
        re.compile(
            r"\binternships?\b|\binterns?\b|\bin[\s-]?service\s+train(?:ing|ee)\b"
            r"|\bwork\s+integrated\s+learning\b|\bvacation\s+work\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Apprenticeship",
        re.compile(r"\bapprentices?\b|\bapprenticeships?\b", re.IGNORECASE),
    ),
]

# Phrases that mean the role is genuinely open to someone with no track record.
_NO_EXPERIENCE_HINTS = (
    "no experience required",
    "no experience necessary",
    "no prior experience",
    "no work experience",
    "without experience",
    "matric only",
    "only matric",
    "grade 12 only",
    "training provided",
    "training from 1st day",
    "full training",
    "we will train",
    "no experience needed",
)


# How much of a description counts as "what this role is" rather than boilerplate
# about the company, its other programmes, or how to apply.
_DESCRIPTION_LEAD_CHARS = 400

# A description can name a programme while describing what the candidate must
# already have done — "completed internship or 1 year's experience" is an
# ordinary job asking for a background, not an internship.
_REQUIREMENT_CONTEXT = re.compile(
    r"(?:completed|complete|prior|previous|past|finished|done|having done)"
    r"[\w\s,'’-]{0,25}?\b(?:learnership|internship|apprenticeship|graduate\s+programme)"
    r"|(?:learnership|internship|apprenticeship)\s+(?:experience|completed)",
    re.IGNORECASE,
)


def _strip_requirement_mentions(text: str) -> str:
    """Blank out programme names that appear as prerequisites, so they can't
    be mistaken for the type of the role being advertised."""
    return _REQUIREMENT_CONTEXT.sub(" ", text)


def detect_opportunity_type(title: str | None, description: str | None) -> str:
    """Classify a listing as an ordinary job or a structured youth programme.

    The title is authoritative. A description only counts near its start: an
    ordinary vacancy will often mention elsewhere that the employer "also runs
    an internship programme", and matching on that mislabels the role.
    """
    title_text = (title or "").lower()
    lead_text = _strip_requirement_mentions(
        (description or "").lower()[:_DESCRIPTION_LEAD_CHARS]
    )

    for opportunity_type, pattern in _OPPORTUNITY_PATTERNS:
        if pattern.search(title_text):
            return opportunity_type

    for opportunity_type, pattern in _OPPORTUNITY_PATTERNS:
        if pattern.search(lead_text):
            return opportunity_type

    return "Job"


def requires_no_experience(title: str | None, description: str | None) -> bool:
    """Whether the listing explicitly says no prior experience is needed.

    These phrases are unambiguous enough to trust anywhere in the text — unlike
    the programme names, nothing says "no experience required" in passing.
    """
    haystack = " ".join(f.lower() for f in (title, description) if f)
    return any(hint in haystack for hint in _NO_EXPERIENCE_HINTS)


def normalise_province(location: str | None) -> str | None:
    """Best-effort map of a free-text SA location onto one of the nine provinces."""
    if not location:
        return None

    lowered = location.lower()

    # An explicit province name in the string always wins over a city guess.
    for province in PROVINCES:
        if province.lower() in lowered:
            return province
    if "kzn" in lowered:
        return "KwaZulu-Natal"

    # Longest city name first, so "east london" is not shadowed by "london".
    for city in sorted(_CITY_TO_PROVINCE, key=len, reverse=True):
        if re.search(rf"\b{re.escape(city)}\b", lowered):
            return _CITY_TO_PROVINCE[city]

    return None


def looks_remote(*fields: str | None) -> bool:
    haystack = " ".join(f.lower() for f in fields if f)
    return any(hint in haystack for hint in _REMOTE_HINTS)


@dataclass
class NormalisedJob:
    """One listing, in the shape the rest of the app understands."""

    source: str
    source_id: str
    apply_url: str
    title: str
    company: str
    description: str | None = None
    description_is_truncated: bool = False
    location: str | None = None
    province: str | None = None
    is_remote: bool = False
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str = "ZAR"
    salary_is_predicted: bool = False
    salary_period: str | None = "month"
    category: str | None = None
    contract_type: str | None = None
    experience_level: str | None = None
    opportunity_type: str = "Job"
    no_experience_required: bool = False
    posted_at: datetime | None = None

    def __post_init__(self):
        if self.province is None:
            self.province = normalise_province(self.location)
        if not self.is_remote:
            self.is_remote = looks_remote(self.location, self.title)

        if self.opportunity_type == "Job":
            self.opportunity_type = detect_opportunity_type(
                self.title, self.description
            )
        if not self.no_experience_required:
            self.no_experience_required = requires_no_experience(
                self.title, self.description
            )

        # A learnership or internship is entry-level by definition, and sources
        # rarely say so explicitly.
        if self.experience_level is None and (
            self.opportunity_type != "Job" or self.no_experience_required
        ):
            self.experience_level = "Entry"


class JobSourceError(Exception):
    """Raised when a provider is unreachable or returns something unusable."""


class JobSource(ABC):
    """Interface every provider implements.

    `name` is persisted on each row as `Job.source`, so it must stay stable.
    """

    name: str = "base"
    #: Whether this provider's terms require linking back to the original post.
    requires_attribution: bool = True

    @abstractmethod
    def fetch(self, query: str | None = None, limit: int = 50) -> list[NormalisedJob]:
        """Return listings for South Africa, newest-first where the API allows."""

    def is_configured(self) -> bool:
        """Whether this source has the credentials it needs to run."""
        return True
