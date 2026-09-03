from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Verification gates the features that send messages on a user's behalf,
    # rather than blocking sign-in — a seeker who can't read their email should
    # still be able to browse jobs.
    is_verified = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    verified_at = Column(DateTime, nullable=True)
