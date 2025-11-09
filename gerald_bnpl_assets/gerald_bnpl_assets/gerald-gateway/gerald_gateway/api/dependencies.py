"""Dependency injection for FastAPI endpoints"""

from fastapi import Request
from gerald_gateway.infrastructure.clients.bank import BankClient
from gerald_gateway.infrastructure.clients.ledger import LedgerClient


def get_request_id(request: Request) -> str:
    """Extract request ID from request state"""
    return getattr(request.state, "request_id", "unknown")


def get_bank_client() -> BankClient:
    """Provide Bank API client instance"""
    return BankClient()


def get_ledger_client() -> LedgerClient:
    """Provide Ledger webhook client instance"""
    return LedgerClient()
