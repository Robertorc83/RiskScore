"""Unit tests for installment plan generation"""

import pytest
from datetime import date, timedelta
from gerald_gateway.domain.installments import generate_installment_plan


def test_generate_installment_plan_equal_split():
    """Test plan with evenly divisible amount"""
    amount = 40000  # $400
    installments = generate_installment_plan(amount)

    assert len(installments) == 4
    assert all(inst.amount_cents == 10000 for inst in installments)  # Each $100
    assert sum(inst.amount_cents for inst in installments) == amount


def test_generate_installment_plan_rounding():
    """Test last installment absorbs remainder"""
    amount = 40003  # $400.03
    installments = generate_installment_plan(amount)

    assert len(installments) == 4
    assert installments[0].amount_cents == 10000
    assert installments[1].amount_cents == 10000
    assert installments[2].amount_cents == 10000
    assert installments[3].amount_cents == 10003  # Last absorbs +3 cents
    assert sum(inst.amount_cents for inst in installments) == amount


def test_generate_installment_plan_dates():
    """Test bi-weekly due dates (14 days apart)"""
    start = date.today()
    installments = generate_installment_plan(40000, start_date=start)

    assert installments[0].due_date == start
    assert installments[1].due_date == start + timedelta(days=14)
    assert installments[2].due_date == start + timedelta(days=28)
    assert installments[3].due_date == start + timedelta(days=42)


def test_generate_installment_plan_zero_amount():
    """Test handling of zero amount (declined)"""
    installments = generate_installment_plan(0)
    assert installments == []
