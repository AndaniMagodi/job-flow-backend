from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.emails import send_password_reset_email, send_verification_email
from app.auth.shema import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.auth.tokens import issue_token, redeem_token
from app.db.session import get_db
from app.models.tokens import EMAIL_VERIFICATION, PASSWORD_RESET
from app.models.users import User

from .jwt import create_access_token
from .security import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# Deliberately identical whether or not the address exists, so this endpoint
# can't be used to find out who has an account.
GENERIC_RESET_RESPONSE = (
    "If that email has an account, a reset link is on its way."
)


def _issue_and_email_verification(db: Session, user: User) -> None:
    token = issue_token(db, user, EMAIL_VERIFICATION)
    send_verification_email(user.email, token)


@router.post("/register", response_model=TokenResponse)
def register(
    body: RegisterRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=body.email, hashed_password=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    # Sent in the background so a slow SMTP server doesn't hold up signup.
    background.add_task(_issue_and_email_verification, db, user)

    return {"access_token": create_access_token({"sub": str(user.id)})}


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # An unverified user can still sign in and browse; verification only gates
    # the features that send messages on their behalf.
    return {"access_token": create_access_token({"sub": str(user.id)})}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/verify-email", response_model=UserResponse)
def verify_email(body: VerifyEmailRequest, db: Session = Depends(get_db)):
    user = redeem_token(db, body.token, EMAIL_VERIFICATION)
    if user is None:
        raise HTTPException(
            status_code=400,
            detail="That link is invalid or has expired. Request a new one.",
        )

    if not user.is_verified:
        user.is_verified = True
        user.verified_at = datetime.utcnow()
        db.commit()
        db.refresh(user)

    return user


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(
    body: ResendVerificationRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == body.email).first()

    # Same response either way — this must not reveal who has an account.
    if user and not user.is_verified:
        background.add_task(_issue_and_email_verification, db, user)

    return {"detail": "If that account needs verifying, a new link is on its way."}


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    body: ForgotPasswordRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == body.email).first()

    if user:
        def _send(u: User = user) -> None:
            token = issue_token(db, u, PASSWORD_RESET)
            send_password_reset_email(u.email, token)

        background.add_task(_send)

    return {"detail": GENERIC_RESET_RESPONSE}


@router.post("/reset-password", response_model=TokenResponse)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = redeem_token(db, body.token, PASSWORD_RESET)
    if user is None:
        raise HTTPException(
            status_code=400,
            detail="That reset link is invalid or has expired. Request a new one.",
        )

    user.hashed_password = hash_password(body.password)

    # Someone who proved control of the mailbox has effectively verified it.
    if not user.is_verified:
        user.is_verified = True
        user.verified_at = datetime.utcnow()

    db.commit()

    return {"access_token": create_access_token({"sub": str(user.id)})}
