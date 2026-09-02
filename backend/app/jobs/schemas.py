from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class JobResponse(BaseModel):
    id: int
    source: str
    apply_url: str
    title: str
    company: str
    description: Optional[str] = None
    description_is_truncated: bool = False
    location: Optional[str] = None
    province: Optional[str] = None
    is_remote: bool = False
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = "ZAR"
    salary_is_predicted: bool = False
    salary_period: Optional[str] = None
    category: Optional[str] = None
    contract_type: Optional[str] = None
    experience_level: Optional[str] = None
    opportunity_type: str = "Job"
    no_experience_required: bool = False
    posted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SalaryBenchmarkResponse(BaseModel):
    """An estimate from comparable adverts — never the employer's own figure."""

    p25: int
    median: int
    p75: int
    sample_size: int
    basis: str
    cohort: str
    confidence: str


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int


class JobFacets(BaseModel):
    """Distinct values actually present in the data, so the UI never offers a
    filter that would return nothing."""

    provinces: list[str]
    categories: list[str]
    experience_levels: list[str]
    contract_types: list[str]
    opportunity_types: list[str]


class SavedJobResponse(BaseModel):
    id: int
    job: JobResponse
    created_at: datetime

    model_config = {"from_attributes": True}
