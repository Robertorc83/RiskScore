"""Bank API HTTP client for fetching transaction history"""

import httpx
from datetime import date
from typing import List
from gerald_gateway.domain.models import Transaction
from gerald_gateway.domain.exceptions import BankAPIError
from gerald_gateway.config import settings


class BankClient:
    """Client for external bank transaction API"""

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        self.base_url = base_url or settings.bank_api_base
        self.timeout = timeout or settings.http_timeout_seconds

    async def get_transactions(self, user_id: str) -> List[Transaction]:
        """
        Fetch 90-day transaction history for a user.

        Raises:
            BankAPIError: On timeout, HTTP errors, or invalid response
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/bank/transactions",
                    params={"user_id": user_id},
                )
                response.raise_for_status()
                data = response.json()

                # Parse and validate transaction data
                return [
                    Transaction(
                        transaction_id=txn["transaction_id"],
                        date=date.fromisoformat(txn["date"]),
                        amount_cents=txn["amount_cents"],
                        type=txn["type"],
                        description=txn["description"],
                        category=txn["category"],
                        merchant=txn["merchant"],
                        balance_cents=txn["balance_cents"],
                        nsf=txn["nsf"],
                    )
                    for txn in data.get("transactions", [])
                ]

            except httpx.TimeoutException as e:
                raise BankAPIError(f"Bank API timeout after {self.timeout}s") from e
            except httpx.HTTPStatusError as e:
                raise BankAPIError(f"Bank API error: {e.response.status_code}") from e
            except (KeyError, ValueError, TypeError) as e:
                raise BankAPIError(f"Invalid transaction data from bank: {e}") from e
