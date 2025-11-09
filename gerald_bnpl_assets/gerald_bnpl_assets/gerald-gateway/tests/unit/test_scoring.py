"""Unit tests for risk scoring logic"""

import pytest
from datetime import date, timedelta
from gerald_gateway.domain.models import Transaction, RiskFactors
from gerald_gateway.domain.scoring import (
    analyze_transactions,
    calculate_risk_score,
    determine_credit_limit,
    make_credit_decision,
)
from gerald_gateway.domain.exceptions import InsufficientDataError


def test_analyze_transactions_avg_balance_carry_forward():
    """Test average daily balance with carry-forward for no-transaction days"""
    base_date = date.today() - timedelta(days=10)
    transactions = [
        Transaction(
            transaction_id="1",
            date=base_date,
            amount_cents=100,
            type="debit",
            description="Test",
            category="test",
            merchant="Test",
            balance_cents=100000,  # $1000
            nsf=False,
        ),
        Transaction(
            transaction_id="2",
            date=base_date + timedelta(days=5),  # 5 days later
            amount_cents=100,
            type="debit",
            description="Test",
            category="test",
            merchant="Test",
            balance_cents=80000,  # $800
            nsf=False,
        ),
    ]

    risk_factors = analyze_transactions(transactions)

    # 5 days at 100000, then 6 days (including last day) at 80000
    # (5 * 100000 + 6 * 80000) / 11 = 90909
    assert risk_factors.avg_daily_balance_cents == 90909


def test_analyze_transactions_income_vs_spend():
    """Test income/spend ratio calculation"""
    base_date = date.today()
    transactions = [
        Transaction(
            transaction_id="1",
            date=base_date,
            amount_cents=300000,  # $3000 income
            type="credit",
            description="Salary",
            category="income",
            merchant="Employer",
            balance_cents=300000,
            nsf=False,
        ),
        Transaction(
            transaction_id="2",
            date=base_date + timedelta(days=1),
            amount_cents=200000,  # $2000 spending
            type="debit",
            description="Rent",
            category="housing",
            merchant="Landlord",
            balance_cents=100000,
            nsf=False,
        ),
    ]

    risk_factors = analyze_transactions(transactions)

    assert risk_factors.total_income_cents == 300000
    assert risk_factors.total_spend_cents == 200000
    assert risk_factors.income_spend_ratio == 1.5  # 3000/2000


def test_analyze_transactions_nsf_count():
    """Test NSF counting (explicit flag + negative balances)"""
    base_date = date.today()
    transactions = [
        Transaction(
            transaction_id="1",
            date=base_date,
            amount_cents=100,
            type="debit",
            description="Test",
            category="test",
            merchant="Test",
            balance_cents=-500,  # Negative balance = NSF
            nsf=False,
        ),
        Transaction(
            transaction_id="2",
            date=base_date + timedelta(days=1),
            amount_cents=100,
            type="debit",
            description="Test",
            category="test",
            merchant="Test",
            balance_cents=1000,
            nsf=True,  # Explicit NSF flag
        ),
    ]

    risk_factors = analyze_transactions(transactions)

    assert risk_factors.nsf_count == 2


def test_calculate_risk_score_boundaries():
    """Test score calculation at different risk levels"""
    # Low risk: high balance, good income ratio, no NSF
    low_risk = RiskFactors(
        avg_daily_balance_cents=150000,  # $1500
        total_income_cents=900000,  # $9000
        total_spend_cents=600000,  # $6000
        income_spend_ratio=1.5,
        nsf_count=0,
        transaction_count=50,
        days_with_transactions=30,
    )
    assert calculate_risk_score(low_risk) == 1.0  # Perfect score

    # High risk: low balance, overspending, NSF
    high_risk = RiskFactors(
        avg_daily_balance_cents=10000,  # $100
        total_income_cents=200000,  # $2000
        total_spend_cents=250000,  # $2500 (spending more than income!)
        income_spend_ratio=0.8,
        nsf_count=3,
        transaction_count=20,
        days_with_transactions=10,
    )
    score = calculate_risk_score(high_risk)
    assert score < 0.5  # Low score


def test_determine_credit_limit_buckets():
    """Test credit limit mapping to score bands"""
    # Decline zone
    approved, limit, band = determine_credit_limit(0.1)
    assert approved is False
    assert limit == 0
    assert band == "high_risk"

    # $100 limit
    approved, limit, band = determine_credit_limit(0.3)
    assert approved is True
    assert limit == 10000
    assert band == "moderate_risk"

    # $400 limit
    approved, limit, band = determine_credit_limit(0.5)
    assert approved is True
    assert limit == 40000
    assert band == "acceptable_risk"

    # $1000 limit
    approved, limit, band = determine_credit_limit(0.8)
    assert approved is True
    assert limit == 100000
    assert band == "low_risk"


def test_make_credit_decision_empty_transactions():
    """Test handling of empty transaction list"""
    with pytest.raises(InsufficientDataError):
        make_credit_decision([])


def test_make_credit_decision_integration():
    """Test complete decision flow"""
    base_date = date.today() - timedelta(days=90)
    # Good customer: steady income, controlled spending, no NSF
    transactions = [
        # Monthly salary
        Transaction(
            "1",
            base_date,
            300000,
            "credit",
            "Salary",
            "income",
            "Employer",
            300000,
            False,
        ),
        Transaction(
            "2",
            base_date + timedelta(days=30),
            300000,
            "credit",
            "Salary",
            "income",
            "Employer",
            500000,
            False,
        ),
        Transaction(
            "3",
            base_date + timedelta(days=60),
            300000,
            "credit",
            "Salary",
            "income",
            "Employer",
            700000,
            False,
        ),
        # Regular spending (less than income)
        Transaction(
            "4",
            base_date + timedelta(days=5),
            50000,
            "debit",
            "Groceries",
            "food",
            "Store",
            250000,
            False,
        ),
    ]

    decision = make_credit_decision(transactions)

    assert decision.approved is True
    assert decision.credit_limit_cents > 0
    assert decision.score > 0.4  # At least moderate score
    assert decision.risk_factors.nsf_count == 0
