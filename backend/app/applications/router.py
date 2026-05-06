from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.auth.dependencies import require_user
from app.models.users import User
from app.models.applications import Application
from app.activities.service import log_activity

from .schemas import ApplicationCreate, ApplicationUpdate, ApplicationResponse, FollowUpUpdate

router = APIRouter(prefix="/applications", tags=["applications"])




@router.get("", response_model=List[ApplicationResponse])
def get_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    return db.query(Application).filter(
        Application.user_id == current_user.id
    ).order_by(Application.id.desc()).all()


@router.post("", response_model=ApplicationResponse)
def create_application(
    body: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    app = Application(**body.model_dump(), user_id=current_user.id)

    db.add(app)
    db.flush()  # get ID before commit

    log_activity(
        db,
        user_id=current_user.id,
        application_id=app.id,
        event="created",
        detail=f"Applied to {app.role} at {app.company}"
    )

    db.commit()
    db.refresh(app)
    return app


@router.patch("/{app_id}/status", response_model=ApplicationResponse)
def update_status(
    app_id: int,
    body: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    if body.status not in {"Applied", "Interview", "Offer", "Rejected"}:
        raise HTTPException(status_code=400, detail="Invalid status")

    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    old_status = app.status
    app.status = body.status

    log_activity(
        db,
        user_id=current_user.id,
        application_id=app.id,
        event="status_changed",
        detail=f"{app.role} at {app.company}: {old_status} → {body.status}"
    )

    db.commit()
    db.refresh(app)
    return app


@router.delete("/{app_id}")
def delete_application(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    db.delete(app)
    db.commit()

    return {"ok": True}


@router.post("/{app_id}/notes", response_model=ApplicationResponse)
def add_note(
    app_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    app.notes = body.get("note", "")

    log_activity(
        db,
        user_id=current_user.id,
        application_id=app.id,
        event="note_added",
        detail=f"{app.role} at {app.company}: {app.notes[:60]}{'...' if len(app.notes or '') > 60 else ''}"
    )

    db.commit()
    db.refresh(app)
    return app

@router.patch("/{app_id}/follow-up", response_model=ApplicationResponse)
def set_follow_up(
    app_id: int,
    body: FollowUpUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    app.follow_up_date = body.follow_up_date

    log_activity(
        db,
        user_id=current_user.id,
        application_id=app.id,
        event="follow_up_set",
        detail=f"Follow-up set for {body.follow_up_date} on {app.role} at {app.company}"
    )

    db.commit()
    db.refresh(app)
    return app

@router.get("/due", response_model=List[ApplicationResponse])
def get_due_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    today = date.today()
    return db.query(Application).filter(
        Application.user_id == current_user.id,
        Application.follow_up_date <= today,
        Application.status.notin_(["Offer", "Rejected"])
    ).order_by(Application.follow_up_date.asc()).all()