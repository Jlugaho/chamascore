from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
import re


# ── AUTH ──────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    phone: str
    national_id: str
    full_name: str
    password: str

    @validator("phone")
    def validate_phone(cls, v):
        if not re.match(r"^(07|01)\d{8}$", v):
            raise ValueError("Invalid Kenyan phone number e.g. 07XXXXXXXX")
        return v

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain an uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain a digit")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    email: str
    phone: str
    full_name: str
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


# ── GROUPS ────────────────────────────────────────────
class GroupCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    contribution_amount: Decimal = Field(..., gt=0)
    meeting_frequency: str
    meeting_day: Optional[str] = None
    created_date: date

class GroupOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    contribution_amount: Decimal
    meeting_frequency: str
    meeting_day: Optional[str]
    created_date: date
    is_active: bool
    class Config:
        from_attributes = True


# ── CONTRIBUTIONS ─────────────────────────────────────
class ContributionCreate(BaseModel):
    group_id: str
    member_id: str
    amount: Decimal = Field(..., gt=0)
    contribution_date: date
    payment_method: str = "mpesa"
    notes: Optional[str] = None

class ContributionOut(BaseModel):
    id: str
    group_id: str
    member_id: str
    amount: Decimal
    contribution_date: date
    payment_method: str
    created_at: datetime
    class Config:
        from_attributes = True


# ── LOANS ─────────────────────────────────────────────
class LoanApplication(BaseModel):
    group_id: str
    amount: Decimal = Field(..., gt=0)
    purpose: str = Field(..., min_length=5)
    repayment_date: date
    interest_rate: Decimal = Field(default=10.0, ge=0, le=100)

class LoanOut(BaseModel):
    id: str
    group_id: str
    member_id: str
    amount: Decimal
    purpose: Optional[str]
    application_date: date
    approval_status: str
    status: str
    interest_rate: Decimal
    class Config:
        from_attributes = True


# ── MEETINGS ──────────────────────────────────────────
class MeetingCreate(BaseModel):
    group_id: str
    title: str = Field(..., min_length=3)
    date: datetime
    agenda: Optional[str] = None

class MeetingOut(BaseModel):
    id: str
    group_id: str
    title: str
    date: datetime
    agenda: Optional[str]
    class Config:
        from_attributes = True


# ── CREDIT SCORES ─────────────────────────────────────
class FeatureDetail(BaseModel):
    value: float
    unit: str
    weight: int
    normalized_score: float
    contribution: float
    rating: str

class CreditScoreOut(BaseModel):
    group_id: str
    group_name: str
    score_date: date
    score_value: int
    score_band: str
    features: Dict[str, FeatureDetail]
    recommendations: List[str]
    calculation_log: Optional[str] = None