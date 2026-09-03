from pydantic import BaseModel, EmailStr, Field

# Short enough not to annoy, long enough to matter. NIST advises length over
# composition rules, so there are no character-class requirements.
MIN_PASSWORD_LENGTH = 8


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_verified: bool

    model_config = {"from_attributes": True}


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)


class MessageResponse(BaseModel):
    detail: str
