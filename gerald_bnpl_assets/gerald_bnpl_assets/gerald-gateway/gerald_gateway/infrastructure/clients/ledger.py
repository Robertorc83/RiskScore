"""Ledger webhook client with exponential backoff retry logic"""

import httpx
import asyncio
from typing import Dict, Any
from gerald_gateway.config import settings
from gerald_gateway.infrastructure.observability.metrics import webhook_latency_histogram, webhook_failure_counter


class LedgerClient:
    """Client for sending webhook events to ledger service"""

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or settings.ledger_webhook_url
        self.max_retries = settings.webhook_max_retries
        self.backoff_base = settings.webhook_backoff_base

    async def send_approval_event(self, payload: Dict[str, Any]) -> None:
        """
        Send BNPL approval event to ledger with retry logic.

        Retry strategy:
        - Exponential backoff: 1s, 2s, 4s, 8s, 16s (base^attempt)
        - Retries on 5xx errors and network failures
        - Tracks latency histogram and failure counter

        Args:
            payload: Event data to send to ledger
        """
        attempt = 0
        async with httpx.AsyncClient() as client:
            while attempt < self.max_retries:
                try:
                    with webhook_latency_histogram.time():
                        response = await client.post(
                            self.webhook_url,
                            json=payload,
                            timeout=10.0,
                        )
                        response.raise_for_status()
                        return  # Success

                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    attempt += 1
                    webhook_failure_counter.inc()

                    if attempt >= self.max_retries:
                        # Final failure after all retries
                        raise

                    # Exponential backoff: 1s, 2s, 4s, 8s, 16s
                    backoff = self.backoff_base * (2 ** (attempt - 1))
                    await asyncio.sleep(backoff)
