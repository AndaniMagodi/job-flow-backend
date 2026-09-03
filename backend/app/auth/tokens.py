"""Issuing and redeeming single-use tokens.

The raw token goes in the email; only its SHA-256 is written to the database.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.tokens import TOKEN_LIFETIMES, VerificationToken
from app.models.users import User


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue_token(db: Session, user: User, purpose: str) -> str:
    """Create a token for `purpose` and return the raw value to email.

    Any outstanding token for the same purpose is consumed first, so an older
    link in an earlier email stops working once a new one is requested.
    """
    now = datetime.utcnow()

    db.query(VerificationToken).filter(
        VerificationToken.user_id == user.id,
        VerificationToken.purpose == purpose,
        VerificationToken.used_at.is_(None),
    ).update({"used_at": now}, synchronize_session=False)

    raw = secrets.token_urlsafe(32)
    db.add(
        VerificationToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=_hash(raw),
            expires_at=now + TOKEN_LIFETIMES[purpose],
        )
    )
    db.commit()
    return raw


def redeem_token(db: Session, raw: str, purpose: str) -> User | None:
    """Consume a token and return its user, or None if it is not usable.

    Marking it used in the same transaction means a link only ever works once,
    even if two requests arrive together.
    """
    record = (
        db.query(VerificationToken)
        .filter(
            VerificationToken.token_hash == _hash(raw),
            VerificationToken.purpose == purpose,
        )
        .one_or_none()
    )

    if record is None or not record.is_usable:
        return None

    record.used_at = datetime.utcnow()
    user = db.get(User, record.user_id)
    db.commit()
    return user
