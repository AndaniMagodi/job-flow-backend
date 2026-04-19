from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pydantic import BaseModel

from app.db.session import get_db
from app.auth.dependencies import require_user
from app.models.users import User
from app.models.activities import Activity

router = APIRouter(prefix="/activities", tags=["activities"])


class ActivityResponse(BaseModel):
    id: int
    application_id: int
    event: str
    detail: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# GET ALL ACTIVITIES
@router.get("", response_model=List[ActivityResponse])
def get_all_activities(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    return db.query(Activity).filter(
        Activity.user_id == current_user.id
    ).order_by(Activity.created_at.desc()).limit(50).all()


# GET BY APPLICATION
@router.get("/application/{app_id}", response_model=List[ActivityResponse])
def get_application_activities(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    return db.query(Activity).filter(
        Activity.application_id == app_id,
        Activity.user_id == current_user.id
    ).order_by(Activity.created_at.desc()).all()