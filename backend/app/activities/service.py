from sqlalchemy.orm import Session
from app.models.activities import Activity

def log_activity(
    db: Session,
    user_id: int,
    application_id: int,
    event: str,
    detail: str | None = None
):
    activity = Activity(
        user_id=user_id,
        application_id=application_id,
        event=event,
        detail=detail,
    )
    db.add(activity)
    # don't commit here — let the caller commit everything together