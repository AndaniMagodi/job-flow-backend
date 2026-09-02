import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.alerts.schemas import AlertCreate, AlertFilters, AlertResponse, AlertUpdate
from app.alerts.service import parse_filters, run_alert
from app.auth.dependencies import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.jobs import JobAlert
from app.models.users import User
from app.notifications import available_channels, normalise_sa_mobile

router = APIRouter(prefix="/alerts", tags=["alerts"])

# One person can only meaningfully act on a handful of alerts, and each one
# costs a message per run.
MAX_ALERTS_PER_USER = 10


def _to_response(alert: JobAlert) -> AlertResponse:
    return AlertResponse(
        id=alert.id,
        name=alert.name,
        filters=AlertFilters(**parse_filters(alert.filters)),
        channel=alert.channel,
        destination=alert.destination,
        is_active=alert.is_active,
        last_notified_at=alert.last_notified_at,
        created_at=alert.created_at,
    )


@router.get("/channels")
def list_channels():
    """Which delivery channels are actually configured on this deployment."""
    return {
        "available": available_channels(),
        "fallback_to_console": settings.notifications_fallback_to_console,
    }


@router.get("", response_model=list[AlertResponse])
def list_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alerts = (
        db.query(JobAlert)
        .filter(JobAlert.user_id == current_user.id)
        .order_by(JobAlert.id.desc())
        .all()
    )
    return [_to_response(a) for a in alerts]


@router.post("", response_model=AlertResponse, status_code=201)
def create_alert(
    body: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = db.query(JobAlert).filter(JobAlert.user_id == current_user.id).count()
    if count >= MAX_ALERTS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"You can have at most {MAX_ALERTS_PER_USER} alerts",
        )

    alert = JobAlert(
        user_id=current_user.id,
        name=body.name,
        filters=json.dumps(body.filters.model_dump(exclude_none=True)),
        channel=body.channel,
        destination=body.destination,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return _to_response(alert)


@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: int,
    body: AlertUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alert = _owned_alert(db, alert_id, current_user)

    if body.name is not None:
        alert.name = body.name
    if body.filters is not None:
        alert.filters = json.dumps(body.filters.model_dump(exclude_none=True))
    if body.destination is not None:
        alert.destination = (
            normalise_sa_mobile(body.destination)
            if alert.channel == "whatsapp"
            else body.destination
        )
    if body.is_active is not None:
        alert.is_active = body.is_active

    db.commit()
    db.refresh(alert)
    return _to_response(alert)


@router.delete("/{alert_id}", status_code=204)
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.delete(_owned_alert(db, alert_id, current_user))
    db.commit()


@router.post("/{alert_id}/preview")
def preview_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Show what this alert would send right now, without sending it."""
    alert = _owned_alert(db, alert_id, current_user)
    return run_alert(db, alert, settings.frontend_url, dry_run=True)


def _owned_alert(db: Session, alert_id: int, user: User) -> JobAlert:
    alert = db.get(JobAlert, alert_id)
    if alert is None or alert.user_id != user.id:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert
