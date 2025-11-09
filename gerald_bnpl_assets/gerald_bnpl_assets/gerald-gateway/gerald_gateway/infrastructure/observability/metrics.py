"""Prometheus metrics for monitoring approval rates, credit limits, and webhook performance"""

from prometheus_client import Counter, Histogram, Gauge

# Decision metrics
decision_counter = Counter(
    "gerald_decision_total",
    "Total BNPL decisions made",
    ["outcome"],  # approved | declined
)

credit_limit_bucket_counter = Counter(
    "gerald_credit_limit_bucket",
    "Credit limits issued by bucket",
    ["bucket"],  # $0, $0-$100, $100-$400, $400+
)

# Webhook metrics
webhook_latency_histogram = Histogram(
    "webhook_latency_seconds",
    "Ledger webhook response time",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

webhook_failure_counter = Counter(
    "webhook_failures_total",
    "Failed webhook deliveries",
)

# Bank API metrics
bank_fetch_failures_counter = Counter(
    "bank_fetch_failures_total",
    "Failed bank API calls",
)

# Service health
request_duration_histogram = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint", "status"],
)


def record_decision(approved: bool, credit_limit_cents: int) -> None:
    """Record decision metrics for monitoring approval rates and credit distribution"""
    outcome = "approved" if approved else "declined"
    decision_counter.labels(outcome=outcome).inc()

    # Bucket credit limits for distribution analysis
    if credit_limit_cents == 0:
        bucket = "$0"
    elif credit_limit_cents <= 10_000:
        bucket = "$0-$100"
    elif credit_limit_cents <= 40_000:
        bucket = "$100-$400"
    else:
        bucket = "$400+"

    credit_limit_bucket_counter.labels(bucket=bucket).inc()
