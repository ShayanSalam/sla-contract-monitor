import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Text, Numeric, Enum, Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    """Single-user auth for now - one account owns everything they upload."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    contracts = relationship("Contract", back_populates="owner")


class Party(Base):
    """A company/individual named in a contract (e.g. 'Acme Logistics', 'Client Co')."""
    __tablename__ = "parties"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    contact_email = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    raw_text = Column(Text, nullable=True)          # extracted text from uploaded file
    original_filename = Column(String, nullable=True)
    status = Column(String, default="uploaded")       # uploaded -> processing -> processed -> failed
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="contracts")
    obligations = relationship("Obligation", back_populates="contract", cascade="all, delete-orphan")

    @property
    def content_length(self) -> int:
        """Character count of raw_text. Used client-side to estimate how
        long extraction will take (chunk count * per-chunk time), so this
        doesn't need its own migration - just exposed via ContractOut."""
        return len(self.raw_text) if self.raw_text else 0


class ObligationStatus(str, enum.Enum):
    pending = "pending"
    upcoming = "upcoming"     # within alert window, not yet breached
    breached = "breached"     # deadline passed, not marked done
    completed = "completed"


class Obligation(Base):
    """A single deadline/duty extracted (or manually entered) from a contract."""
    __tablename__ = "obligations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    contract_id = Column(UUID(as_uuid=False), ForeignKey("contracts.id"), nullable=False)
    party_id = Column(UUID(as_uuid=False), ForeignKey("parties.id"), nullable=True)

    description = Column(Text, nullable=False)
    deadline = Column(DateTime, nullable=False)
    penalty_amount = Column(Numeric(12, 2), nullable=True)
    penalty_currency = Column(String, default="KWD")
    status = Column(Enum(ObligationStatus), default=ObligationStatus.pending)
    is_ai_extracted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("Contract", back_populates="obligations")
    party = relationship("Party")
    alerts = relationship("AlertLog", back_populates="obligation", cascade="all, delete-orphan")


class AlertLog(Base):
    """Every time the system flags/notifies about an obligation, it's recorded here.
    This audit trail is what makes the system trustworthy for compliance use cases."""
    __tablename__ = "alerts_log"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    obligation_id = Column(UUID(as_uuid=False), ForeignKey("obligations.id"), nullable=False)
    alert_type = Column(String, nullable=False)   # "upcoming_reminder" | "breach_notice"
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)

    obligation = relationship("Obligation", back_populates="alerts")
