"""Installment plan generation for BNPL repayment"""

from datetime import date, timedelta
from typing import List
from gerald_gateway.domain.models import Installment


def generate_installment_plan(
    amount_cents: int,
    num_installments: int = 4,
    interval_days: int = 14,
    start_date: date | None = None,
) -> List[Installment]:
    """
    Generate equal bi-weekly installments for BNPL repayment.

    Requirements:
    - 4 equal installments by default
    - 14 days apart (bi-weekly)
    - Last installment absorbs rounding remainder (≤ num_installments-1 cents drift)

    Args:
        amount_cents: Total amount to split into installments
        num_installments: Number of payments (default 4)
        interval_days: Days between payments (default 14)
        start_date: First due date (default: today + interval_days)

    Returns:
        List of Installment objects with due dates and amounts

    Example:
        $400.03 → [$100.00, $100.00, $100.00, $100.03]
        40003 cents / 4 = 10000 base, remainder 3
        Last installment: 10000 + 3 = 10003
    """
    if amount_cents <= 0:
        return []

    if start_date is None:
        start_date = date.today() + timedelta(days=interval_days)

    # Calculate base amount and remainder
    base_amount = amount_cents // num_installments
    remainder = amount_cents % num_installments

    installments = []
    for i in range(num_installments):
        due_date = start_date + timedelta(days=i * interval_days)

        # Last installment absorbs remainder to ensure exact total
        amount = base_amount + (remainder if i == num_installments - 1 else 0)

        installments.append(Installment(due_date=due_date, amount_cents=amount))

    return installments
