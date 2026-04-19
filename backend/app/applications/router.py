from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.auth.dependencies import require_user
from app.models.users import User
from app.models.applications import Application
from app.activities.service import log_activity

from .schemas import ApplicationCreate, ApplicationUpdate, ApplicationResponse

router = APIRouter(prefix="/applications", tags=["applications"])


# GET ALL
@router.get("", response_model=List[ApplicationResponse])
def get_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    return db.query(Application).filter(
        Application.user_id == current_user.id
    ).order_by(Application.id.desc()).all()


# CREATE
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


# UPDATE STATUS
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
        detail=f"{old_status} → {body.status}"
    )

    db.commit()
    db.refresh(app)
    return app


# DELETE
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


# ADD NOTE
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
        detail=app.notes[:80]
    )

    db.commit()
    db.refresh(app)
    return app