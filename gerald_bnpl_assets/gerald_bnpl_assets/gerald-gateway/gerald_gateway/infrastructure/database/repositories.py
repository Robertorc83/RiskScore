"""Data access layer for BNPL entities"""

import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from gerald_gateway.infrastructure.database.models import BNPLDecision, BNPLPlan, BNPLInstallment
from gerald_gateway.domain.models import CreditDecision, Installment


class DecisionRepository:
    """Repository for BNPL decisions"""

    def __init__(self, db: Session):
        self.db = db

    def create_decision(
        self,
        user_id: str,
        requested_cents: int,
        decision: CreditDecision,
        amount_granted_cents: int,
    ) -> BNPLDecision:
        """Persist credit decision to database"""
        db_decision = BNPLDecision(
            user_id=user_id,
            requested_cents=requested_cents,
            approved=decision.approved,
            credit_limit_cents=decision.credit_limit_cents,
            amount_granted_cents=amount_granted_cents,
            score_numeric=decision.score,
            score_band=decision.score_band,
            risk_factors={
                "avg_daily_balance_cents": decision.risk_factors.avg_daily_balance_cents,
                "total_income_cents": decision.risk_factors.total_income_cents,
                "total_spend_cents": decision.risk_factors.total_spend_cents,
                "income_spend_ratio": decision.risk_factors.income_spend_ratio,
                "nsf_count": decision.risk_factors.nsf_count,
            },
        )
        self.db.add(db_decision)
        self.db.flush()  # Get ID without committing
        return db_decision

    def get_decisions_by_user(self, user_id: str, limit: int = 10) -> List[BNPLDecision]:
        """Fetch recent decisions for a user"""
        return (
            self.db.query(BNPLDecision)
            .filter(BNPLDecision.user_id == user_id)
            .order_by(BNPLDecision.created_at.desc())
            .limit(limit)
            .all()
        )


class PlanRepository:
    """Repository for repayment plans"""

    def __init__(self, db: Session):
        self.db = db

    def create_plan(
        self,
        decision_id: uuid.UUID,
        user_id: str,
        total_cents: int,
        installments: List[Installment],
    ) -> BNPLPlan:
        """Create repayment plan with installments"""
        db_plan = BNPLPlan(
            decision_id=decision_id,
            user_id=user_id,
            total_cents=total_cents,
        )
        self.db.add(db_plan)
        self.db.flush()

        # Create installments
        for inst in installments:
            db_installment = BNPLInstallment(
                plan_id=db_plan.id,
                due_date=inst.due_date,
                amount_cents=inst.amount_cents,
            )
            self.db.add(db_installment)

        return db_plan

    def get_plan_by_id(self, plan_id: uuid.UUID) -> Optional[BNPLPlan]:
        """Fetch plan with installments"""
        return (
            self.db.query(BNPLPlan)
            .filter(BNPLPlan.id == plan_id)
            .first()
        )
