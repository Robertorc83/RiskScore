"""Risk scoring engine - core business logic for credit decisions"""

from datetime import date, timedelta
from typing import List, Dict
from gerald_gateway.domain.models import Transaction, RiskFactors, CreditDecision
from gerald_gateway.domain.exceptions import InsufficientDataError
from gerald_gateway.utils.date_utils import generate_date_range


def analyze_transactions(transactions: List[Transaction]) -> RiskFactors:
    """
    Analyze transaction history and extract risk metrics.

    Requirements:
    - Average daily balance with carry-forward for no-transaction days
    - Total income vs spend (credits vs debits)
    - NSF/overdraft count
    """
    if not transactions:
        raise InsufficientDataError("No transaction history available")

    # Sort by date
    sorted_txns = sorted(transactions, key=lambda t: t.date)
    start_date = sorted_txns[0].date
    end_date = sorted_txns[-1].date

    # Build daily balance map with carry-forward
    balance_by_date: Dict[date, int] = {}
    for txn in sorted_txns:
        balance_by_date[txn.date] = txn.balance_cents

    # Carry forward balances for days with no transactions
    all_dates = generate_date_range(start_date, end_date)
    last_known_balance = 0
    daily_balances = []

    for day in all_dates:
        if day in balance_by_date:
            last_known_balance = balance_by_date[day]
        daily_balances.append(last_known_balance)

    # Calculate average daily balance
    avg_daily_balance = sum(daily_balances) // len(daily_balances) if daily_balances else 0

    # Income vs spend
    total_income = sum(t.amount_cents for t in transactions if t.type == "credit")
    total_spend = sum(t.amount_cents for t in transactions if t.type == "debit")

    # Income/spend ratio (avoid division by zero)
    income_spend_ratio = total_income / total_spend if total_spend > 0 else 0.0

    # NSF/overdraft count: explicit nsf flag OR negative balance after transaction
    nsf_count = sum(
        1 for t in transactions
        if t.nsf or t.balance_cents < 0
    )

    # Transaction activity metrics
    unique_dates = set(t.date for t in transactions)

    return RiskFactors(
        avg_daily_balance_cents=avg_daily_balance,
        total_income_cents=total_income,
        total_spend_cents=total_spend,
        income_spend_ratio=income_spend_ratio,
        nsf_count=nsf_count,
        transaction_count=len(transactions),
        days_with_transactions=len(unique_dates),
    )


def calculate_risk_score(risk_factors: RiskFactors) -> float:
    """
    Calculate risk score from 0.0 (highest risk) to 1.0 (lowest risk).

    Scoring weights:
    - 40%: Average balance (higher is better)
    - 40%: Income/spend ratio (>1.0 is better, means more income than spending)
    - 20%: NSF penalty (any NSF significantly hurts score)

    Thresholds rationale:
    - avg_balance_baseline = $1000 (100,000 cents): Users maintaining $1k+ balance are stable
    - income_ratio > 1.0: Spending within means
    - NSF = 0: Any overdraft is a major red flag
    """
    # Balance component: normalize to 0-1, cap at $1000
    balance_baseline = 100_000  # $1000 in cents
    balance_score = min(risk_factors.avg_daily_balance_cents / balance_baseline, 1.0)

    # Income/spend component: >1.0 is ideal, cap at 1.0
    income_score = min(risk_factors.income_spend_ratio, 1.0)

    # NSF penalty: binary - any NSF is bad
    nsf_score = 1.0 if risk_factors.nsf_count == 0 else 0.0

    # Weighted score
    score = (0.4 * balance_score) + (0.4 * income_score) + (0.2 * nsf_score)

    return round(score, 3)


def determine_credit_limit(score: float) -> tuple[bool, int, str]:
    """
    Map risk score to credit limit buckets.

    Score bands (empirically derived thresholds):
    - 0.0 - 0.2: Decline (high risk - low balance, overspending, or NSF)
    - 0.2 - 0.4: $100 limit (moderate risk - thin file or inconsistent income)
    - 0.4 - 0.7: $400 limit (acceptable risk - stable income/balance)
    - 0.7+:      $1000 limit (low risk - strong financials)

    Returns: (approved, credit_limit_cents, score_band)
    """
    if score < 0.2:
        return False, 0, "high_risk"
    elif score < 0.4:
        return True, 10_000, "moderate_risk"  # $100
    elif score < 0.7:
        return True, 40_000, "acceptable_risk"  # $400
    else:
        return True, 100_000, "low_risk"  # $1000


def make_credit_decision(transactions: List[Transaction]) -> CreditDecision:
    """
    Main entry point: analyze transactions and make credit decision.

    Returns complete CreditDecision with approval, limit, score, and factors.
    """
    risk_factors = analyze_transactions(transactions)
    score = calculate_risk_score(risk_factors)
    approved, credit_limit, score_band = determine_credit_limit(score)

    return CreditDecision(
        approved=approved,
        credit_limit_cents=credit_limit,
        score=score,
        score_band=score_band,
        risk_factors=risk_factors,
    )
