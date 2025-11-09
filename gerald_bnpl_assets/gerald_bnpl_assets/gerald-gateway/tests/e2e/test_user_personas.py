"""
E2E tests for 5 user personas testing real bank API integration.

These tests require the mock bank server to be running:
    make mock-up

User personas:
- user_good: Excellent credit, high approval expected
- user_overdraft: NSF history, decline expected
- user_thin: Limited history, conservative approval
- user_gig: Irregular income, moderate approval
- user_highutil: High spending, credit cap scenario
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_user_good_approval(client: TestClient):
    """
    user_good: Strong transaction history
    Expected: Approve with high credit limit
    """
    response = client.post(
        "/v1/decision",
        json={"user_id": "user_good", "amount_cents_requested": 40000},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["approved"] is True, "user_good should be approved"
    assert data["credit_limit_cents"] >= 40000, "Should have sufficient credit limit"
    assert data["amount_granted_cents"] == 40000
    assert data["plan_id"] is not None


@pytest.mark.integration
def test_user_overdraft_decline(client: TestClient):
    """
    user_overdraft: NSF/overdraft history
    Expected: Decline due to high risk
    """
    response = client.post(
        "/v1/decision",
        json={"user_id": "user_overdraft", "amount_cents_requested": 40000},
    )

    assert response.status_code == 200
    data = response.json()
    # May be declined or given very low limit
    if not data["approved"]:
        assert data["credit_limit_cents"] == 0
        assert data["amount_granted_cents"] == 0
        assert data["plan_id"] is None
    else:
        # If approved, limit should be low due to NSF history
        assert data["credit_limit_cents"] <= 10000


@pytest.mark.integration
def test_user_thin_conservative(client: TestClient):
    """
    user_thin: Limited transaction history
    Expected: Conservative approval or decline
    """
    response = client.post(
        "/v1/decision",
        json={"user_id": "user_thin", "amount_cents_requested": 40000},
    )

    assert response.status_code == 200
    data = response.json()
    # Thin file: either declined or low limit
    if data["approved"]:
        assert data["credit_limit_cents"] <= 40000
    else:
        assert data["credit_limit_cents"] == 0


@pytest.mark.integration
def test_user_gig_irregular_income(client: TestClient):
    """
    user_gig: Gig worker with irregular income
    Expected: Moderate approval based on average income
    """
    response = client.post(
        "/v1/decision",
        json={"user_id": "user_gig", "amount_cents_requested": 30000},
    )

    assert response.status_code == 200
    data = response.json()
    # Gig workers can be approved if average income is positive
    if data["approved"]:
        assert data["credit_limit_cents"] > 0


@pytest.mark.integration
def test_user_highutil_credit_cap(client: TestClient):
    """
    user_highutil: High spending utilization
    Expected: Granted amount capped to credit limit
    """
    response = client.post(
        "/v1/decision",
        json={"user_id": "user_highutil", "amount_cents_requested": 100000},  # Request $1000
    )

    assert response.status_code == 200
    data = response.json()

    if data["approved"]:
        # Granted should be min(requested, credit_limit)
        assert data["amount_granted_cents"] <= data["credit_limit_cents"]
        assert data["amount_granted_cents"] <= 100000


@pytest.mark.integration
def test_installment_plan_generation(client: TestClient):
    """Test that installment plan is correctly generated for approved user"""
    decision_response = client.post(
        "/v1/decision",
        json={"user_id": "user_good", "amount_cents_requested": 40000},
    )

    data = decision_response.json()
    if data["approved"] and data["plan_id"]:
        plan_response = client.get(f"/v1/plan/{data['plan_id']}")
        plan_data = plan_response.json()

        # Verify 4 bi-weekly installments
        assert len(plan_data["installments"]) == 4
        assert sum(i["amount_cents"] for i in plan_data["installments"]) == data["amount_granted_cents"]

        # Verify dates are 14 days apart
        from datetime import datetime
        dates = [datetime.fromisoformat(i["due_date"]) for i in plan_data["installments"]]
        for i in range(1, len(dates)):
            days_diff = (dates[i] - dates[i-1]).days
            assert days_diff == 14, "Installments should be 14 days apart"
