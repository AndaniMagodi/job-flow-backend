from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.notifications import normalise_sa_mobile


class AlertFilters(BaseModel):
    """The same shape the browse page uses."""

    q: Optional[str] = None
    province: Optional[str] = None
    is_remote: Optional[bool] = None
    category: Optional[str] = None
    experience_level: Optional[str] = None
    contract_type: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    opportunity_type: Optional[str] = None
    no_experience_required: Optional[bool] = None


class AlertCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    filters: AlertFilters = Field(default_factory=AlertFilters)
    channel: str = "whatsapp"
    destination: str

    @field_validator("destination")
    @classmethod
    def check_destination(cls, v: str, info) -> str:
        # Catch a mistyped number when it is saved, not weeks later when an
        # alert silently fails to arrive.
        if (info.data or {}).get("channel", "whatsapp") == "whatsapp":
            return normalise_sa_mobile(v)
        return v


class AlertUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    filters: Optional[AlertFilters] = None
    destination: Optional[str] = None
    is_active: Optional[bool] = None


class AlertResponse(BaseModel):
    id: int
    name: str
    filters: AlertFilters
    channel: str
    destination: str
    is_active: bool
    last_notified_at: Optional[datetime] = None
    created_at: datetime
