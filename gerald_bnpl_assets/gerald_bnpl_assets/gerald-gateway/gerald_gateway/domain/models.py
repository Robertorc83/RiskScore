"""Domain models - pure Python dataclasses representing business entities"""

from dataclasses import dataclass
from datetime import date
from typing import List


@dataclass
class Transaction:
    """Bank transaction from external API"""

    transaction_id: str
    date: date
    amount_cents: int
    type: str  # "credit" or "debit"
    description: str
    category: str
    merchant: str
    balance_cents: int
    nsf: bool


@dataclass
class RiskFactors:
    """Calculated risk metrics used for scoring"""

    avg_daily_balance_cents: int
    total_income_cents: int
    total_spend_cents: int
    income_spend_ratio: float
    nsf_count: int
    transaction_count: int
    days_with_transactions: int


@dataclass
class CreditDecision:
    """Output of risk assessment"""

    approved: bool
    credit_limit_cents: int
    score: float
    score_band: str
    risk_factors: RiskFactors


@dataclass
class Installment:
    """Single payment in a repayment plan"""

    due_date: date
    amount_cents: int
