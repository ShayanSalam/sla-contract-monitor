from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict


# ---- Party ----
class PartyCreate(BaseModel):
    name: str
    contact_email: Optional[EmailStr] = None


class PartyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    contact_email: Optional[str] = None


# ---- Contract ----
class ContractCreate(BaseModel):
    title: str
    raw_text: Optional[str] = None


class ContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    status: str
    original_filename: Optional[str] = None
    created_at: datetime
    content_length: int = 0


# ---- Obligation ----
class ObligationCreate(BaseModel):
    contract_id: str
    party_id: Optional[str] = None
    description: str
    deadline: datetime
    penalty_amount: Optional[Decimal] = None
    penalty_currency: str = "USD"


class ObligationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    contract_id: str
    description: str
    deadline: datetime
    penalty_amount: Optional[Decimal] = None
    penalty_currency: str
    status: str
    is_ai_extracted: bool


class ObligationStatusUpdate(BaseModel):
    status: str  # e.g., "completed", "pending"


# ---- AlertLog ----
class AlertLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    obligation_id: str
    alert_type: str
    message: str
    sent_at: datetime


# ---- Auth ----
class UserCreate(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
