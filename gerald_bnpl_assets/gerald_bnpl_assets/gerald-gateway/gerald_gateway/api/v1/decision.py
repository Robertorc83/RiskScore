"""POST /v1/decision - BNPL credit decision endpoint"""

import time
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session

from gerald_gateway.api.v1.schemas import DecisionRequest, DecisionResponse
from gerald_gateway.api.dependencies import get_bank_client, get_ledger_client, get_request_id
from gerald_gateway.infrastructure.database.session import get_db
from gerald_gateway.infrastructure.database.repositories import DecisionRepository, PlanRepository
from gerald_gateway.infrastructure.clients.bank import BankClient
from gerald_gateway.infrastructure.clients.ledger import LedgerClient
from gerald_gateway.domain.scoring import make_credit_decision
from gerald_gateway.domain.installments import generate_installment_plan
from gerald_gateway.domain.exceptions import BankAPIError, InsufficientDataError
from gerald_gateway.infrastructure.observability.metrics import record_decision, bank_fetch_failures_counter
from gerald_gateway.infrastructure.observability.logging import log_decision

router = APIRouter()


@router.post("/decision", response_model=DecisionResponse)
async def create_decision(
    request_body: DecisionRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    bank_client: BankClient = Depends(get_bank_client),
    ledger_client: LedgerClient = Depends(get_ledger_client),
):
    """
    Make BNPL credit decision based on transaction history.

    Flow:
    1. Fetch 90-day transaction history from bank API
    2. Analyze risk and calculate credit limit
    3. Create installment plan if approved
    4. Persist decision + plan to database
    5. Send async webhook to ledger
    6. Return decision response
    """
    start_time = time.time()
    request_id = get_request_id(request)

    try:
        # 1. Fetch transaction history
        transactions = await bank_client.get_transactions(request_body.user_id)

        # 2. Make credit decision
        decision = make_credit_decision(transactions)

        # 3. Determine amount to grant (min of requested and limit)
        amount_granted = (
            min(request_body.amount_cents_requested, decision.credit_limit_cents)
            if decision.approved
            else 0
        )

        # 4. Persist decision
        decision_repo = DecisionRepository(db)
        db_decision = decision_repo.create_decision(
            user_id=request_body.user_id,
            requested_cents=request_body.amount_cents_requested,
            decision=decision,
            amount_granted_cents=amount_granted,
        )

        # 5. Create repayment plan if approved
        plan_id = None
        if decision.approved and amount_granted > 0:
            installments = generate_installment_plan(amount_granted)
            plan_repo = PlanRepository(db)
            db_plan = plan_repo.create_plan(
                decision_id=db_decision.id,
                user_id=request_body.user_id,
                total_cents=amount_granted,
                installments=installments,
            )
            plan_id = str(db_plan.id)

            # 6. Schedule async webhook to ledger
            background_tasks.add_task(
                ledger_client.send_approval_event,
                {
                    "event": "BNPL_APPROVED",
                    "decision_id": str(db_decision.id),
                    "plan_id": plan_id,
                    "user_id": request_body.user_id,
                    "amount_cents": amount_granted,
                },
            )

        db.commit()

        # Record metrics and logs
        duration_ms = (time.time() - start_time) * 1000
        record_decision(decision.approved, decision.credit_limit_cents)
        log_decision(request_id, request_body.user_id, decision.approved, decision.credit_limit_cents, duration_ms)

        return DecisionResponse(
            approved=decision.approved,
            credit_limit_cents=decision.credit_limit_cents,
            amount_granted_cents=amount_granted,
            plan_id=plan_id,
        )

    except BankAPIError as e:
        bank_fetch_failures_counter.inc()
        db.rollback()
        logging.error(f"Bank API error: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=503, detail="Bank service unavailable")

    except InsufficientDataError as e:
        db.rollback()
        logging.warning(f"Insufficient data: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        db.rollback()
        logging.error(f"Unexpected error: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail="Internal server error")
