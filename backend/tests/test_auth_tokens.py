"""Tests for verification and password-reset tokens.

These guard the security-relevant behaviour: single use, expiry, and the fact
that only a hash is ever stored.
"""

import hashlib
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.tokens import issue_token, redeem_token
from app.db.base import Base
from app.models.tokens import EMAIL_VERIFICATION, PASSWORD_RESET, VerificationToken
from app.models.users import User


@pytest.fixture()
def db():
    # SQLite in memory: these helpers use no Postgres-specific behaviour.
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture()
def user(db):
    u = User(email="seeker@example.com", hashed_password="x")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


class TestIssue:
    def test_raw_token_is_never_stored(self, db, user):
        raw = issue_token(db, user, EMAIL_VERIFICATION)
        stored = db.query(VerificationToken).one()

        assert stored.token_hash != raw
        assert stored.token_hash == hashlib.sha256(raw.encode()).hexdigest()

    def test_issuing_again_invalidates_the_previous_link(self, db, user):
        first = issue_token(db, user, EMAIL_VERIFICATION)
        issue_token(db, user, EMAIL_VERIFICATION)

        assert redeem_token(db, first, EMAIL_VERIFICATION) is None

    def test_purposes_are_independent(self, db, user):
        verify = issue_token(db, user, EMAIL_VERIFICATION)
        issue_token(db, user, PASSWORD_RESET)

        assert redeem_token(db, verify, EMAIL_VERIFICATION) is not None


class TestRedeem:
    def test_valid_token_returns_its_user(self, db, user):
        raw = issue_token(db, user, EMAIL_VERIFICATION)
        assert redeem_token(db, raw, EMAIL_VERIFICATION).id == user.id

    def test_a_token_only_works_once(self, db, user):
        raw = issue_token(db, user, PASSWORD_RESET)

        assert redeem_token(db, raw, PASSWORD_RESET) is not None
        assert redeem_token(db, raw, PASSWORD_RESET) is None

    def test_expired_token_is_refused(self, db, user):
        raw = issue_token(db, user, PASSWORD_RESET)
        record = db.query(VerificationToken).one()
        record.expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.commit()

        assert redeem_token(db, raw, PASSWORD_RESET) is None

    def test_a_verification_token_cannot_reset_a_password(self, db, user):
        # Otherwise a link from a signup email would be enough to take over
        # the account.
        raw = issue_token(db, user, EMAIL_VERIFICATION)
        assert redeem_token(db, raw, PASSWORD_RESET) is None

    def test_unknown_token_is_refused(self, db):
        assert redeem_token(db, "not-a-real-token", EMAIL_VERIFICATION) is None
