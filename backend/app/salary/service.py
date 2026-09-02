"""Salary benchmarks computed from our own corpus.

Roughly three quarters of South African listings publish no salary at all,
which leaves seekers negotiating blind. We can't fix that at the source, but we
can say what comparable advertised roles actually pay, from the listings we
already hold.

Every figure is explicitly an estimate from other adverts — never presented as
the employer's own number.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Float, and_, func, or_
from sqlalchemy.orm import Session

from app.models.jobs import Job

# Below this, a percentile is noise rather than a benchmark.
MIN_SAMPLE = 5

# How wide the quartile range may be before it stops being useful. A cohort
# spanning R12k-R60k tells a seeker nothing they can negotiate with, and
# publishing it anyway would be worse than showing nothing.
MAX_SPREAD_RATIO = 4.0

# Thresholds for how much weight to put on a benchmark, shown to the user.
HIGH_CONFIDENCE_SAMPLE = 20
HIGH_CONFIDENCE_SPREAD = 2.5
MEDIUM_CONFIDENCE_SAMPLE = 10
MEDIUM_CONFIDENCE_SPREAD = 3.0

# How far we widen the comparison group before giving up, most specific first.
# Each step trades precision for a usable sample.
COHORT_STEPS = ("category+province+level", "category+province", "category", "province")


@dataclass
class SalaryBenchmark:
    """A monthly Rand range for comparable advertised roles."""

    p25: float
    median: float
    p75: float
    sample_size: int
    #: Which comparison group produced this, e.g. "IT roles in Gauteng".
    basis: str
    cohort: str
    #: high | medium | low — how tightly the comparable adverts cluster.
    confidence: str

    def as_dict(self) -> dict:
        return {
            "p25": round(self.p25),
            "median": round(self.median),
            "p75": round(self.p75),
            "sample_size": self.sample_size,
            "basis": self.basis,
            "cohort": self.cohort,
            "confidence": self.confidence,
        }


def _spread_ratio(p25: float, p75: float) -> float:
    return p75 / p25 if p25 > 0 else float("inf")


def _confidence(sample_size: int, spread: float) -> str:
    if sample_size >= HIGH_CONFIDENCE_SAMPLE and spread <= HIGH_CONFIDENCE_SPREAD:
        return "high"
    if sample_size >= MEDIUM_CONFIDENCE_SAMPLE and spread <= MEDIUM_CONFIDENCE_SPREAD:
        return "medium"
    return "low"


def _midpoint_column():
    """A single figure per listing, in Rand per month.

    Listings quote a range, one end of a range, or a flat number. The midpoint
    of whatever is present is the fairest single comparison point. Salaries are
    stored annually, so divide to get the monthly figure people think in.
    """
    lo = func.coalesce(Job.salary_min, Job.salary_max)
    hi = func.coalesce(Job.salary_max, Job.salary_min)
    return (func.cast(lo, Float) + func.cast(hi, Float)) / 2.0 / 12.0


def _describe(category: str | None, province: str | None, level: str | None, cohort: str) -> str:
    """Describe exactly the group that was measured.

    Only mention a dimension the cohort actually filtered on — calling a
    province-wide sample "IT roles" would overstate how comparable it is.
    """
    role = f"{category} roles" if category and "category" in cohort else "roles"
    seniority = f" at {level.lower()} level" if level and "level" in cohort else ""
    where = f" in {province}" if province and "province" in cohort else " across South Africa"
    return f"{role}{seniority}{where}"


def get_benchmark(
    db: Session,
    category: str | None,
    province: str | None = None,
    experience_level: str | None = None,
) -> SalaryBenchmark | None:
    """Widen the comparison group until it is big enough to mean something."""
    for cohort in COHORT_STEPS:
        filters = [
            or_(Job.salary_min.isnot(None), Job.salary_max.isnot(None)),
            # Predicted salaries are the aggregator's own guess; benchmarking
            # our estimate on their estimate would compound the error.
            Job.salary_is_predicted.is_(False),
        ]

        if "category" in cohort:
            if not category:
                continue
            filters.append(Job.category == category)
        if "province" in cohort:
            if not province:
                continue
            filters.append(Job.province == province)
        if "level" in cohort:
            if not experience_level:
                continue
            filters.append(Job.experience_level == experience_level)

        midpoint = _midpoint_column()
        row = (
            db.query(
                func.percentile_cont(0.25).within_group(midpoint).label("p25"),
                func.percentile_cont(0.50).within_group(midpoint).label("median"),
                func.percentile_cont(0.75).within_group(midpoint).label("p75"),
                func.count().label("n"),
            )
            .filter(and_(*filters))
            .one()
        )

        if row.n < MIN_SAMPLE or not row.median:
            continue

        p25, median, p75 = float(row.p25), float(row.median), float(row.p75)
        spread = _spread_ratio(p25, p75)

        # Too scattered to be a benchmark. Widening would only mix in more
        # unrelated roles, so stop rather than publish a meaningless range.
        if spread > MAX_SPREAD_RATIO:
            continue

        return SalaryBenchmark(
            p25=p25,
            median=median,
            p75=p75,
            sample_size=int(row.n),
            basis=_describe(category, province, experience_level, cohort),
            cohort=cohort,
            confidence=_confidence(int(row.n), spread),
        )

    return None


def benchmark_for_job(db: Session, job: Job) -> SalaryBenchmark | None:
    """Only meaningful for a listing that doesn't state its own salary."""
    if job.salary_min is not None or job.salary_max is not None:
        return None
    return get_benchmark(db, job.category, job.province, job.experience_level)
