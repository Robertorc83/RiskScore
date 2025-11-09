"""GET /v1/decision/history - Fetch user's decision history"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from gerald_gateway.api.v1.schemas import HistoryResponse, HistoryItem
from gerald_gateway.infrastructure.database.session import get_db
from gerald_gateway.infrastructure.database.repositories import DecisionRepository

router = APIRouter()


@router.get("/decision/history", response_model=HistoryResponse)
def get_decision_history(
    user_id: str = Query(..., description="User identifier"),
    db: Session = Depends(get_db),
):
    """
    Retrieve recent credit decisions for a user.

    Returns:
        List of decisions (approved/declined) with credit limits
    """
    decision_repo = DecisionRepository(db)
    decisions = decision_repo.get_decisions_by_user(user_id, limit=20)

    history_items = [
        HistoryItem(
            decision_id=str(d.id),
            approved=d.approved,
            credit_limit_cents=d.credit_limit_cents,
            amount_granted_cents=d.amount_granted_cents,
            created_at=d.created_at.isoformat(),
        )
        for d in decisions
    ]

    return HistoryResponse(user_id=user_id, decisions=history_items)
