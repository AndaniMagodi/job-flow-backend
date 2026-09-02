"""Job source registry.

`get_active_sources()` is the only thing the rest of the app should use — which
providers are live is a config decision, not a code decision.
"""

from app.core.config import settings
from app.jobs.sources.adzuna import AdzunaSource
from app.jobs.sources.base import (
    JobSource,
    JobSourceError,
    NormalisedJob,
    normalise_province,
)
from app.jobs.sources.greenhouse import GreenhouseSource
from app.jobs.sources.seed import SeedSource

_REGISTRY: dict[str, type[JobSource]] = {
    AdzunaSource.name: AdzunaSource,
    GreenhouseSource.name: GreenhouseSource,
    SeedSource.name: SeedSource,
}


def get_source(name: str) -> JobSource:
    try:
        return _REGISTRY[name]()
    except KeyError:
        raise JobSourceError(
            f"Unknown job source '{name}'. Known: {', '.join(sorted(_REGISTRY))}"
        ) from None


def get_active_sources() -> list[JobSource]:
    """Sources named in JOB_SOURCES that actually have their credentials."""
    active = []
    for name in settings.job_sources.split(","):
        name = name.strip()
        if not name:
            continue
        source = get_source(name)
        if source.is_configured():
            active.append(source)
    return active


__all__ = [
    "AdzunaSource",
    "GreenhouseSource",
    "SeedSource",
    "JobSource",
    "JobSourceError",
    "NormalisedJob",
    "normalise_province",
    "get_source",
    "get_active_sources",
]
