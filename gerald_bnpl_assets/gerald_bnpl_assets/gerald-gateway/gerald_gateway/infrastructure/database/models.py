"""SQLAlchemy ORM models matching db/schema.sql"""

import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, BigInteger, Boolean, Float, DateTime, Date, Integer, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class BNPLDecision(Base):
    """BNPL credit decision record"""

    __tablename__ = "bnpl_decision"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Text, nullable=False, index=True)
    requested_cents = Column(BigInteger, nullable=False)
    approved = Column(Boolean, nullable=False)
    credit_limit_cents = Column(BigInteger, nullable=False)
    amount_granted_cents = Column(BigInteger, nullable=False)
    score_numeric = Column(Float, nullable=True)
    score_band = Column(Text, nullable=True)
    risk_factors = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    plans = relationship("BNPLPlan", back_populates="decision", cascade="all, delete-orphan")


class BNPLPlan(Base):
    """Repayment plan for approved BNPL"""

    __tablename__ = "bnpl_plan"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_id = Column(UUID(as_uuid=True), ForeignKey("bnpl_decision.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Text, nullable=False, index=True)
    total_cents = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    decision = relationship("BNPLDecision", back_populates="plans")
    installments = relationship("BNPLInstallment", back_populates="plan", cascade="all, delete-orphan")


class BNPLInstallment(Base):
    """Individual installment within a payment plan"""

    __tablename__ = "bnpl_installment"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("bnpl_plan.id", ondelete="CASCADE"), nullable=False)
    due_date = Column(Date, nullable=False)
    amount_cents = Column(BigInteger, nullable=False)
    status = Column(Text, nullable=False, default="scheduled")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    plan = relationship("BNPLPlan", back_populates="installments")


class OutboundWebhook(Base):
    """Webhook delivery queue with retry tracking"""

    __tablename__ = "outbound_webhook"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(Text, nullable=False)
    payload = Column(JSON, nullable=False)
    target_url = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="pending")
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
