"""Pydantic schemas for API request/response validation"""

from pydantic import BaseModel, Field, UUID4
from datetime import date
from typing import List, Optional


class DecisionRequest(BaseModel):
    """Request body for POST /v1/decision"""

    user_id: str = Field(..., min_length=1, description="User identifier")
    amount_cents_requested: int = Field(..., gt=0, description="Requested credit amount in cents")


class DecisionResponse(BaseModel):
    """Response for POST /v1/decision"""

    approved: bool
    credit_limit_cents: int
    amount_granted_cents: int
    plan_id: Optional[str] = None


class InstallmentSchema(BaseModel):
    """Single installment in a repayment plan"""

    due_date: date
    amount_cents: int
    status: str = "scheduled"


class PlanResponse(BaseModel):
    """Response for GET /v1/plan/{plan_id}"""

    plan_id: str
    user_id: str
    total_cents: int
    installments: List[InstallmentSchema]
    created_at: str


class HistoryItem(BaseModel):
    """Single decision in history"""

    decision_id: str
    approved: bool
    credit_limit_cents: int
    amount_granted_cents: int
    created_at: str


class HistoryResponse(BaseModel):
    """Response for GET /v1/decision/history"""

    user_id: str
    decisions: List[HistoryItem]
