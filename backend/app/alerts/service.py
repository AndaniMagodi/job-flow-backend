"""Run job alerts: find new matching listings and notify the seeker."""

from __future__ import annotations

import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.jobs import Job, JobAlert
from app.notifications import Message, NotificationError, get_channel

logger = logging.getLogger(__name__)

# WhatsApp bodies get truncated by the client, and nobody reads a wall of jobs
# on a phone. Link out for the rest.
MAX_JOBS_PER_MESSAGE = 3

# Only these keys are honoured from a saved filter, so a stored blob can never
# reach the query builder with something unexpected.
ALLOWED_FILTERS = {
    "q",
    "province",
    "is_remote",
    "category",
    "experience_level",
    "contract_type",
    "salary_min",
    "salary_max",
    "opportunity_type",
    "no_experience_required",
}


def parse_filters(raw: str) -> dict:
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if k in ALLOWED_FILTERS and v not in (None, "")}


def find_new_matches(db: Session, alert: JobAlert, limit: int = 20) -> list[Job]:
    """Listings matching this alert that appeared since it last ran."""
    # Imported here to avoid a circular import at module load.
    from app.jobs.router import _apply_filters

    query = _apply_filters(db.query(Job), **parse_filters(alert.filters))
    return (
        query.filter(Job.id > alert.last_seen_job_id)
        .order_by(Job.id.desc())
        .limit(limit)
        .all()
    )


def build_message_body(alert: JobAlert, jobs: list[Job], base_url: str) -> str:
    lines = [
        f"{len(jobs)} new {'job' if len(jobs) == 1 else 'jobs'} matching "
        f"\"{alert.name}\" on JobFlow:"
    ]

    for job in jobs[:MAX_JOBS_PER_MESSAGE]:
        where = job.location or job.province or "South Africa"
        lines.append(f"• {job.title} — {job.company}, {where}")

    remaining = len(jobs) - MAX_JOBS_PER_MESSAGE
    if remaining > 0:
        lines.append(f"…and {remaining} more.")

    lines.append(f"{base_url}/jobs")
    return "\n".join(lines)


def run_alert(db: Session, alert: JobAlert, base_url: str, dry_run: bool = False) -> dict:
    """Check one alert and notify if there is anything new.

    The watermark only advances on a successful send, so a delivery failure
    means the seeker gets those jobs on the next run rather than losing them.
    """
    jobs = find_new_matches(db, alert)

    if not jobs:
        return {"alert_id": alert.id, "matched": 0, "sent": False}

    body = build_message_body(alert, jobs, base_url)

    if dry_run:
        return {"alert_id": alert.id, "matched": len(jobs), "sent": False, "preview": body}

    try:
        get_channel(alert.channel).send(
            Message(to=alert.destination, body=body, url=f"{base_url}/jobs")
        )
    except NotificationError as e:
        logger.warning("alert %s could not be delivered: %s", alert.id, e)
        return {"alert_id": alert.id, "matched": len(jobs), "sent": False, "error": str(e)}

    alert.last_seen_job_id = max(job.id for job in jobs)
    alert.last_notified_at = datetime.utcnow()
    db.commit()

    return {"alert_id": alert.id, "matched": len(jobs), "sent": True}


def run_all_alerts(db: Session, base_url: str) -> dict:
    """Entry point for the scheduler."""
    alerts = db.query(JobAlert).filter(JobAlert.is_active.is_(True)).all()
    results = [run_alert(db, alert, base_url) for alert in alerts]

    return {
        "alerts_checked": len(results),
        "notifications_sent": sum(1 for r in results if r["sent"]),
        "results": results,
    }
