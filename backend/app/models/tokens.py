"""Single-use tokens for email verification and password resets.

Only a hash of each token is stored. A database leak then exposes nothing
usable: an attacker would still need the original value, which exists only in
the email we sent.
"""

from datetime import datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

EMAIL_VERIFICATION = "email_verification"
PASSWORD_RESET = "password_reset"

# Verification links are convenience; reset links are a way into the account,
# so they expire far sooner.
TOKEN_LIFETIMES = {
    EMAIL_VERIFICATION: timedelta(days=3),
    PASSWORD_RESET: timedelta(hours=1),
}


class VerificationToken(Base):
    __tablename__ = "verification_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    purpose: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    #: SHA-256 of the token we emailed. The raw value is never stored.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @property
    def is_usable(self) -> bool:
        return self.used_at is None and self.expires_at > datetime.utcnow()
