from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Job(Base):
    """A job listing pulled from an external source.

    Listings are owned by whoever published them, not by us, so `apply_url`
    always points back at the original posting — we never host the apply flow.
    """

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_jobs_source_source_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Provenance
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    apply_url: Mapped[str] = mapped_column(Text(), nullable=False)

    # Core listing
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    description_is_truncated: Mapped[bool] = mapped_column(Boolean, default=False)

    # South African location. `province` is normalised to the nine provinces so
    # the browse filters stay stable across sources that spell cities freely.
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    province: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Money is always ZAR here; kept as a column so a future non-SA source
    # can't silently mix currencies into the same filters.
    salary_min: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(3), default="ZAR")
    salary_is_predicted: Mapped[bool] = mapped_column(Boolean, default=False)
    salary_period: Mapped[str | None] = mapped_column(String(20), nullable=True)

    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    contract_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Job | Learnership | Internship | Graduate programme | Apprenticeship.
    # Structured youth programmes are how a large share of South Africans enter
    # the labour market, so they are filterable in their own right.
    opportunity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Job", server_default="Job", index=True
    )
    no_experience_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )

    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SavedJob(Base):
    __tablename__ = "saved_jobs"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_saved_jobs_user_job"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # The saved-jobs list renders each listing, so eager-load it rather than
    # firing one query per saved row.
    job: Mapped["Job"] = relationship(lazy="joined")


class JobMatch(Base):
    """A persisted CV-to-job match produced by the LLM.

    Every run is stored, so a repeat view of the same job is free and the
    match history stays auditable.
    """

    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", "cv_hash", name="uq_job_matches_user_job_cv"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Lets us reuse a stored match when the CV has not changed.
    cv_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    match_score: Mapped[int] = mapped_column(Integer, nullable=False)
    verdict: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[str] = mapped_column(Text(), nullable=False)
    # JSON-encoded lists — kept as text so this works on any Postgres version.
    strengths: Mapped[str] = mapped_column(Text(), nullable=False, default="[]")
    gaps: Mapped[str] = mapped_column(Text(), nullable=False, default="[]")
    suggestions: Mapped[str] = mapped_column(Text(), nullable=False, default="[]")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class JobAlert(Base):
    """A saved search that notifies the seeker when matching jobs appear.

    This is what turns a job board into something people come back to: most
    seekers can't check a site daily, and the roles they want are gone in days.
    """

    __tablename__ = "job_alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    #: The same filter object the browse page uses, JSON-encoded.
    filters: Mapped[str] = mapped_column(Text(), nullable=False, default="{}")

    channel: Mapped[str] = mapped_column(String(30), nullable=False, default="whatsapp")
    #: E.164 mobile number for WhatsApp, validated on save.
    destination: Mapped[str] = mapped_column(String(120), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Job ids are monotonic for new listings, so this is a cheap, exact
    # watermark — no risk of re-notifying on a re-sync that merely updates rows.
    last_seen_job_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
