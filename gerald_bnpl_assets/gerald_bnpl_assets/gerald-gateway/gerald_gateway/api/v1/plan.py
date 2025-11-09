"""GET /v1/plan/{plan_id} - Fetch repayment plan details"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from gerald_gateway.api.v1.schemas import PlanResponse, InstallmentSchema
from gerald_gateway.infrastructure.database.session import get_db
from gerald_gateway.infrastructure.database.repositories import PlanRepository

router = APIRouter()


@router.get("/plan/{plan_id}", response_model=PlanResponse)
def get_plan(plan_id: str, db: Session = Depends(get_db)):
    """
    Retrieve repayment plan with installment schedule.

    Returns:
        Plan details with 4 bi-weekly installments
    """
    try:
        plan_uuid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan ID format")

    plan_repo = PlanRepository(db)
    plan = plan_repo.get_plan_by_id(plan_uuid)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    installments = [
        InstallmentSchema(
            due_date=inst.due_date,
            amount_cents=inst.amount_cents,
            status=inst.status,
        )
        for inst in plan.installments
    ]

    return PlanResponse(
        plan_id=str(plan.id),
        user_id=plan.user_id,
        total_cents=plan.total_cents,
        installments=installments,
        created_at=plan.created_at.isoformat(),
    )
