"""Schemas the LLM must conform to.

These are the contract: the model's raw text is parsed and validated against
them before anything downstream sees it, so a malformed generation fails here
rather than leaking into the UI.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

Verdict = Literal["Strong match", "Good match", "Partial match", "Weak match"]


class JobMatchResult(BaseModel):
    match_score: int = Field(ge=0, le=100)
    verdict: Verdict
    summary: str
    strengths: list[str] = Field(default_factory=list, max_length=6)
    gaps: list[str] = Field(default_factory=list, max_length=6)
    suggestions: list[str] = Field(default_factory=list, max_length=4)


class SearchFilters(BaseModel):
    """A natural-language query parsed into filters we can run against the DB."""

    keywords: Optional[str] = None
    province: Optional[str] = None
    is_remote: Optional[bool] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    category: Optional[str] = None
    experience_level: Optional[str] = None
    contract_type: Optional[str] = None
    # Plain-English readback so the UI can show what it understood, and the
    # user can correct it rather than wondering why results look odd.
    interpretation: str = ""


class MatchRequest(BaseModel):
    job_id: int
    cv_text: str = Field(min_length=50, max_length=20000)


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
