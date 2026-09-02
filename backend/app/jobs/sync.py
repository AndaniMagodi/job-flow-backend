"""Pull listings from the active sources into our own database.

User searches hit our Postgres, never the provider — that keeps Adzuna's
~1k calls/month for the sync job instead of burning it on page loads.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from sqlalchemy.orm import Session

from app.jobs.sources import JobSource, JobSourceError, NormalisedJob, get_active_sources
from app.models.jobs import Job

# Flush in batches so a large sync doesn't hold thousands of pending inserts.
BATCH_SIZE = 200


def sync_jobs(
    db: Session,
    query: str | None = None,
    limit_per_source: int = 50,
    sources: list[JobSource] | None = None,
) -> dict:
    """Fetch and upsert. Returns a per-source report; one bad source never
    aborts the others."""
    sources = sources if sources is not None else get_active_sources()
    report: dict = {"created": 0, "updated": 0, "skipped": 0, "sources": {}, "errors": {}}

    for source in sources:
        try:
            fetched = source.fetch(query=query, limit=limit_per_source)
        except JobSourceError as e:
            report["errors"][source.name] = str(e)
            continue

        created = updated = skipped = 0
        # Providers page over a shifting result set, so the same listing can
        # come back on two pages of one run. Without this the second copy is a
        # pending duplicate insert and the whole commit fails on the unique key.
        seen: set[tuple[str, str]] = set()

        for index, normalised in enumerate(fetched, start=1):
            key = (normalised.source, normalised.source_id)
            if key in seen:
                skipped += 1
                continue
            seen.add(key)

            if _upsert(db, normalised):
                created += 1
            else:
                updated += 1

            if index % BATCH_SIZE == 0:
                db.flush()

        db.commit()
        report["created"] += created
        report["updated"] += updated
        report["skipped"] += skipped
        report["sources"][source.name] = {
            "created": created,
            "updated": updated,
            "duplicates_skipped": skipped,
        }

    return report


def _upsert(db: Session, normalised: NormalisedJob) -> bool:
    """Insert or refresh one listing. True if it was newly created."""
    existing = (
        db.query(Job)
        .filter(Job.source == normalised.source, Job.source_id == normalised.source_id)
        .one_or_none()
    )

    fields = asdict(normalised)
    fields["synced_at"] = datetime.utcnow()

    if existing is None:
        db.add(Job(**fields))
        return True

    for key, value in fields.items():
        setattr(existing, key, value)
    return False
