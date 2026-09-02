"""Sample South African listings for local development and demos.

These are ILLUSTRATIVE, NOT REAL VACANCIES. Every row is synthetic and its
`apply_url` is a placeholder, so the UI can label them clearly and nobody
mistakes a demo row for a job they can actually apply to. Real listings come
from AdzunaSource / GreenhouseSource.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.jobs.sources.base import JobSource, NormalisedJob

# Kept relative so seeded data never looks stale in a demo.
_NOW = datetime.utcnow()


def _days_ago(days: int) -> datetime:
    return _NOW - timedelta(days=days)


# (title, company, location, category, level, contract, salary_min, salary_max, days_ago, description)
_LISTINGS = [
    (
        "Junior Python Developer", "Yoco", "Cape Town, Western Cape", "IT", "Junior",
        "Full time", 360000, 480000, 2,
        "Join the payments team building APIs that move money for small South African "
        "businesses. You'll work in Python and FastAPI against PostgreSQL, ship to "
        "production weekly, and pair with senior engineers.\n\nRequirements: 1-2 years "
        "Python, comfort with REST APIs and SQL, a Git workflow, and willingness to learn "
        "payments domain. Bonus: Docker, pytest, or any exposure to PCI environments.",
    ),
    (
        "Data Analyst", "Discovery", "Sandton, Gauteng", "Data", "Intermediate",
        "Full time", 480000, 660000, 1,
        "Support the health analytics team with reporting on member behaviour and claims "
        "trends. Heavy SQL, Power BI dashboards, and stakeholder presentations.\n\n"
        "Requirements: 3+ years in analytics, advanced SQL, one of Python or R, and "
        "demonstrated experience turning messy data into decisions. BCom, BSc or "
        "equivalent.",
    ),
    (
        "Backend Engineer (Go)", "Luno", "Cape Town, Western Cape", "IT", "Senior",
        "Full time", 840000, 1200000, 4,
        "Build and operate the services behind a crypto exchange serving millions of "
        "customers across Africa and Asia. Distributed systems, strong consistency "
        "requirements, and real on-call.\n\nRequirements: 5+ years backend, production Go "
        "or a comparable statically typed language, solid grasp of concurrency and "
        "database internals.",
    ),
    (
        "Registered Nurse - ICU", "Netcare", "Durban, KwaZulu-Natal", "Healthcare",
        "Intermediate", "Full time", 320000, 440000, 3,
        "ICU nursing post at a private hospital, rotating shifts. You'll manage "
        "ventilated patients, run haemodynamic monitoring, and support the "
        "multidisciplinary team.\n\nRequirements: SANC registration as a Professional "
        "Nurse, ICU qualification or 2+ years proven ICU experience, valid BLS/ACLS.",
    ),
    (
        "Financial Accountant", "Sygnia", "Cape Town, Western Cape", "Finance",
        "Intermediate", "Full time", 540000, 720000, 6,
        "Own the month-end close for a listed asset manager: reconciliations, IFRS "
        "reporting, and audit liaison.\n\nRequirements: CA(SA) or completed SAICA "
        "articles, IFRS working knowledge, advanced Excel. Fund accounting exposure is "
        "a strong advantage.",
    ),
    (
        "Customer Support Consultant", "Takealot", "Cape Town, Western Cape", "Support",
        "Entry", "Full time", 180000, 240000, 1,
        "Front-line support for online shoppers: order queries, returns, and delivery "
        "escalations over email, chat and phone.\n\nRequirements: Matric, excellent "
        "written English, one additional South African language an advantage, and the "
        "patience to handle a busy queue.",
    ),
    (
        "Mechanical Engineer", "Sasol", "Secunda, Mpumalanga", "Engineering",
        "Intermediate", "Full time", 660000, 900000, 8,
        "Maintenance and reliability engineering on rotating equipment in a "
        "petrochemical plant. Root-cause analysis, shutdown planning, and contractor "
        "oversight.\n\nRequirements: BEng/BTech Mechanical, ECSA registration or "
        "eligibility, 3+ years heavy industry. Own transport essential.",
    ),
    (
        "Frontend Developer (React)", "Investec", "Sandton, Gauteng", "IT",
        "Intermediate", "Full time", 600000, 840000, 5,
        "Build the private banking web experience in React and TypeScript, working "
        "closely with design and the API teams.\n\nRequirements: 3+ years React, strong "
        "TypeScript, testing discipline, and an eye for accessible UI. Banking or "
        "regulated-industry exposure helpful but not required.",
    ),
    (
        "Foundation Phase Teacher", "Curro Holdings", "Pretoria, Gauteng", "Education",
        "Entry", "Full time", 240000, 320000, 7,
        "Grade 1-3 classroom teaching at an independent school, following CAPS with "
        "additional enrichment.\n\nRequirements: BEd Foundation Phase or PGCE, SACE "
        "registration, and a police clearance certificate.",
    ),
    (
        "Site Agent - Civil", "WBHO", "Gqeberha, Eastern Cape", "Construction",
        "Senior", "Contract", 720000, 960000, 10,
        "Run day-to-day delivery on a roads and earthworks contract: programme, "
        "subcontractors, quality and site safety.\n\nRequirements: NDip/BTech Civil, 6+ "
        "years site experience with at least 2 as Site Agent, SACPCMP registration "
        "advantageous.",
    ),
    (
        "Digital Marketing Specialist", "Nando's", "Johannesburg, Gauteng", "Marketing",
        "Intermediate", "Full time", 420000, 560000, 2,
        "Plan and run paid social and search campaigns for a brand with strong opinions "
        "about tone. Reporting on CAC, ROAS and brand lift.\n\nRequirements: 3+ years "
        "performance marketing, hands-on Meta and Google Ads, comfort with GA4.",
    ),
    (
        "Warehouse Supervisor", "Shoprite", "Brackenfell, Western Cape", "Logistics",
        "Intermediate", "Full time", 260000, 340000, 4,
        "Supervise a shift in a high-volume distribution centre: picking accuracy, "
        "stock integrity, and team performance.\n\nRequirements: Matric plus a supply "
        "chain qualification, 3+ years warehouse supervision, WMS experience "
        "(SAP EWM an advantage).",
    ),
    (
        "DevOps Engineer", "Standard Bank", "Johannesburg, Gauteng", "IT", "Senior",
        "Full time", 780000, 1080000, 6,
        "Platform engineering for core banking workloads: Kubernetes, Terraform, and "
        "CI/CD pipelines under a strict change-control regime.\n\nRequirements: 5+ years "
        "in infrastructure or platform roles, production Kubernetes, IaC, and a solid "
        "security posture.",
    ),
    (
        "Human Resources Business Partner", "Old Mutual", "Cape Town, Western Cape",
        "HR", "Senior", "Full time", 620000, 820000, 9,
        "Partner with business unit leadership on organisational design, employee "
        "relations, and transformation targets.\n\nRequirements: Honours in HR or "
        "Industrial Psychology, 6+ years HR generalist, working knowledge of the LRA, "
        "BCEA and EE Act.",
    ),
    (
        "Diesel Mechanic", "Barloworld", "Rustenburg, North West", "Trades",
        "Intermediate", "Full time", 300000, 420000, 5,
        "Service and repair earthmoving equipment on and off site for mining clients.\n\n"
        "Requirements: Qualified Diesel Mechanic (trade tested), 3+ years on heavy "
        "equipment, valid driver's licence, medically fit for mine site access.",
    ),
    (
        "Junior Data Scientist", "Capitec", "Stellenbosch, Western Cape", "Data",
        "Junior", "Full time", 480000, 640000, 3,
        "Build and monitor credit and fraud models with the decision science team.\n\n"
        "Requirements: BSc Honours in Statistics, Data Science, Applied Maths or "
        "similar; Python (pandas, scikit-learn); SQL. Internship or project portfolio "
        "counts.",
    ),
    (
        "Call Centre Agent", "Vodacom", "Midrand, Gauteng", "Support", "Entry",
        "Full time", 150000, 200000, 1,
        "Inbound customer service for prepaid and contract subscribers.\n\n"
        "Requirements: Matric, clear telephone manner, ability to work shifts. "
        "Multilingual candidates preferred - isiZulu, Sesotho or Xitsonga a strong plus.",
    ),
    (
        "Product Manager", "Naspers", "Cape Town, Western Cape", "Product", "Senior",
        "Full time", 900000, 1300000, 7,
        "Own a consumer product line end to end: discovery, roadmap, and outcomes.\n\n"
        "Requirements: 5+ years product management on consumer software, evidence of "
        "shipping and measuring, comfort with experimentation and analytics.",
    ),
    (
        "Bookkeeper", "Independent SME", "Polokwane, Limpopo", "Finance", "Junior",
        "Part time", 156000, 216000, 11,
        "Day-to-day books for a group of small retail businesses: creditors, debtors, "
        "VAT201 and payroll support.\n\nRequirements: Bookkeeping certificate or "
        "equivalent, Sage or Xero experience, SARS eFiling familiarity.",
    ),
    (
        "Agricultural Technician", "Karsten Group", "Upington, Northern Cape",
        "Agriculture", "Intermediate", "Full time", 280000, 380000, 12,
        "Support irrigation scheduling and crop monitoring across table grape and "
        "citrus blocks.\n\nRequirements: NDip Agriculture or similar, familiarity with "
        "soil moisture probes and irrigation systems, valid driver's licence.",
    ),
    (
        "Remote Software Engineer", "OfferZen Partner", "Remote, South Africa", "IT",
        "Intermediate", "Full time", 720000, 1020000, 2,
        "Fully remote engineering role with a distributed team, South African hours.\n\n"
        "Requirements: 4+ years building web applications, strong fundamentals in one "
        "modern stack, self-directed working style, and reliable connectivity.",
    ),
    (
        "Legal Advisor", "Sanlam", "Bloemfontein, Free State", "Legal", "Intermediate",
        "Full time", 560000, 760000, 8,
        "Advise business units on contracts, regulatory compliance and dispute "
        "resolution in a long-term insurance context.\n\nRequirements: LLB and admitted "
        "attorney, 3+ years post-admission, exposure to FAIS or FICA an advantage.",
    ),
]


class SeedSource(JobSource):
    """Synthetic sample data. Never presented to users as a real vacancy."""

    name = "seed"
    requires_attribution = False

    def fetch(self, query: str | None = None, limit: int = 50) -> list[NormalisedJob]:
        jobs = [self._build(index, row) for index, row in enumerate(_LISTINGS)]

        if query:
            needle = query.lower()
            jobs = [
                j
                for j in jobs
                if needle in j.title.lower()
                or needle in j.company.lower()
                or needle in (j.description or "").lower()
            ]

        return jobs[:limit]

    @staticmethod
    def _build(index: int, row: tuple) -> NormalisedJob:
        (
            title, company, location, category, level, contract,
            salary_min, salary_max, days_ago, description,
        ) = row

        return NormalisedJob(
            source=SeedSource.name,
            source_id=f"seed-{index}",
            # Deliberately non-clickable: this is sample data, not a real vacancy.
            apply_url="",
            title=title,
            company=company,
            description=f"[SAMPLE LISTING - not a real vacancy]\n\n{description}",
            description_is_truncated=False,
            location=location,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_is_predicted=False,
            salary_period="year",
            category=category,
            contract_type=contract,
            experience_level=level,
            posted_at=_days_ago(days_ago),
        )
