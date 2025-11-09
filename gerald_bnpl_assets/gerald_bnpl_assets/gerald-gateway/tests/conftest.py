"""Pytest fixtures for testing"""

import pytest
from datetime import date, timedelta
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from gerald_gateway.api.main import create_app
from gerald_gateway.infrastructure.database.models import Base
from gerald_gateway.infrastructure.database.session import get_db
from gerald_gateway.domain.models import Transaction


# Test database
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Create test database and session"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db: Session) -> TestClient:
    """Create FastAPI test client with test database"""
    app = create_app()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def sample_transactions() -> list[Transaction]:
    """Sample transaction history for testing"""
    base_date = date.today() - timedelta(days=90)
    transactions = []

    # Simulate monthly salary deposits
    for month in range(3):
        transactions.append(
            Transaction(
                transaction_id=f"credit_{month}",
                date=base_date + timedelta(days=month * 30),
                amount_cents=300000,  # $3000 income
                type="credit",
                description="Salary Deposit",
                category="income",
                merchant="Employer",
                balance_cents=350000,
                nsf=False,
            )
        )

    # Regular spending
    for day in range(0, 90, 7):
        transactions.append(
            Transaction(
                transaction_id=f"debit_{day}",
                date=base_date + timedelta(days=day),
                amount_cents=50000,  # $500 weekly spending
                type="debit",
                description="Groceries",
                category="groceries",
                merchant="Supermarket",
                balance_cents=300000,
                nsf=False,
            )
        )

    return transactions
