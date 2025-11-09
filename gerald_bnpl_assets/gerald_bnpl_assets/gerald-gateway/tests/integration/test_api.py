"""Integration tests for API endpoints"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import date, timedelta
from fastapi.testclient import TestClient
from gerald_gateway.domain.models import Transaction


@pytest.fixture
def mock_transactions():
    """Mock bank API response with good transaction history"""
    base_date = date.today() - timedelta(days=90)
    return [
        Transaction(
            transaction_id=f"tx_{i}",
            date=base_date + timedelta(days=i * 10),
            amount_cents=300000 if i % 3 == 0 else 50000,
            type="credit" if i % 3 == 0 else "debit",
            description="Transaction",
            category="test",
            merchant="Test Merchant",
            balance_cents=200000,
            nsf=False,
        )
        for i in range(10)
    ]


def test_health_endpoint(client: TestClient):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_metrics_endpoint(client: TestClient):
    """Test Prometheus metrics endpoint"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "gerald_decision_total" in response.text


@patch("gerald_gateway.infrastructure.clients.bank.BankClient.get_transactions")
@patch("gerald_gateway.infrastructure.clients.ledger.LedgerClient.send_approval_event")
async def test_decision_endpoint_approval(
    mock_ledger: AsyncMock,
    mock_bank: AsyncMock,
    client: TestClient,
    mock_transactions: list[Transaction],
):
    """Test POST /v1/decision with approval"""
    mock_bank.return_value = mock_transactions
    mock_ledger.return_value = None

    response = client.post(
        "/v1/decision",
        json={"user_id": "user_good", "amount_cents_requested": 40000},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["approved"] is True
    assert data["credit_limit_cents"] > 0
    assert data["amount_granted_cents"] == 40000
    assert data["plan_id"] is not None


@patch("gerald_gateway.infrastructure.clients.bank.BankClient.get_transactions")
async def test_decision_endpoint_decline(
    mock_bank: AsyncMock,
    client: TestClient,
):
    """Test POST /v1/decision with decline (insufficient history)"""
    base_date = date.today()
    # Very poor transaction history: low balance, NSF
    mock_bank.return_value = [
        Transaction(
            transaction_id="1",
            date=base_date,
            amount_cents=1000,
            type="debit",
            description="Test",
            category="test",
            merchant="Test",
            balance_cents=-500,  # Negative balance
            nsf=True,
        )
    ]

    response = client.post(
        "/v1/decision",
        json={"user_id": "user_bad", "amount_cents_requested": 40000},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["approved"] is False
    assert data["credit_limit_cents"] == 0
    assert data["amount_granted_cents"] == 0
    assert data["plan_id"] is None


@patch("gerald_gateway.infrastructure.clients.bank.BankClient.get_transactions")
@patch("gerald_gateway.infrastructure.clients.ledger.LedgerClient.send_approval_event")
async def test_get_plan_endpoint(
    mock_ledger: AsyncMock,
    mock_bank: AsyncMock,
    client: TestClient,
    mock_transactions: list[Transaction],
):
    """Test GET /v1/plan/{plan_id}"""
    mock_bank.return_value = mock_transactions
    mock_ledger.return_value = None

    # First create a decision
    decision_response = client.post(
        "/v1/decision",
        json={"user_id": "user_good", "amount_cents_requested": 40000},
    )
    plan_id = decision_response.json()["plan_id"]

    # Then fetch the plan
    plan_response = client.get(f"/v1/plan/{plan_id}")

    assert plan_response.status_code == 200
    data = plan_response.json()
    assert data["plan_id"] == plan_id
    assert data["total_cents"] == 40000
    assert len(data["installments"]) == 4
    assert sum(inst["amount_cents"] for inst in data["installments"]) == 40000


def test_get_plan_not_found(client: TestClient):
    """Test GET /v1/plan/{plan_id} with invalid ID"""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/v1/plan/{fake_uuid}")
    assert response.status_code == 404


@patch("gerald_gateway.infrastructure.clients.bank.BankClient.get_transactions")
@patch("gerald_gateway.infrastructure.clients.ledger.LedgerClient.send_approval_event")
async def test_get_history_endpoint(
    mock_ledger: AsyncMock,
    mock_bank: AsyncMock,
    client: TestClient,
    mock_transactions: list[Transaction],
):
    """Test GET /v1/decision/history"""
    mock_bank.return_value = mock_transactions
    mock_ledger.return_value = None

    # Create a few decisions
    client.post(
        "/v1/decision",
        json={"user_id": "test_user", "amount_cents_requested": 40000},
    )
    client.post(
        "/v1/decision",
        json={"user_id": "test_user", "amount_cents_requested": 20000},
    )

    # Fetch history
    response = client.get("/v1/decision/history?user_id=test_user")

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "test_user"
    assert len(data["decisions"]) >= 2
