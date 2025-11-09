# Architecture Documentation

## System Overview

Gerald BNPL Gateway is a production-grade microservice implementing credit decisioning and repayment plan management following **Clean Architecture** principles.

---

## 🏛️ Architectural Patterns

### Clean Architecture (Layered Design)

```
┌──────────────────────────────────────────────────────────┐
│                   API Layer (Presentation)                │
│  FastAPI, HTTP, Request/Response, Middleware             │
│  Dependencies: FastAPI, Pydantic                          │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│                   Domain Layer (Business Logic)           │
│  Pure Python, No External Dependencies                    │
│  Risk Scoring, Installment Generation, Business Rules     │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│              Infrastructure Layer (External I/O)          │
│  PostgreSQL, HTTP Clients, Metrics, Logging               │
│  Dependencies: SQLAlchemy, httpx, prometheus-client       │
└──────────────────────────────────────────────────────────┘
```

**Benefits:**
- **Testability**: Domain logic has zero external dependencies
- **Maintainability**: Business rules isolated from infrastructure concerns
- **Flexibility**: Easy to swap databases, APIs, or frameworks

---

## 🎯 Design Decisions

### 1. Why Clean Architecture?

**Decision**: Separate domain logic from infrastructure

**Rationale:**
- Risk scoring algorithm should be testable without database or HTTP mocks
- Business rules change frequently (e.g., credit thresholds)
- Infrastructure changes rarely (e.g., moving from Postgres to DynamoDB)
- Enables fast unit tests (no I/O needed)

**Example:**
```python
# domain/scoring.py - No external dependencies
def calculate_risk_score(risk_factors: RiskFactors) -> float:
    balance_score = min(risk_factors.avg_daily_balance_cents / 100_000, 1.0)
    # Pure calculation, easily testable
```

---

### 2. Risk Scoring Algorithm

**Decision**: Weighted scoring with empirical thresholds

**Components:**
1. **Average Daily Balance** (40% weight)
   - Baseline: $1000 (100,000 cents)
   - Rationale: Users maintaining ≥$1k balance show financial stability
   - Carry-forward: Days without transactions use last known balance

2. **Income/Spend Ratio** (40% weight)
   - Formula: `total_credits / total_debits`
   - Rationale: Ratio >1.0 means living within means
   - Cap at 1.0 to prevent outliers

3. **NSF Penalty** (20% weight)
   - Binary: 1.0 if zero NSF events, 0.0 otherwise
   - Rationale: Any overdraft is a major red flag

**Credit Limit Buckets:**
- Decline if score < 0.2 (e.g., NSF + low balance)
- $100 if 0.2 ≤ score < 0.4 (thin file or irregular income)
- $400 if 0.4 ≤ score < 0.7 (stable income/balance)
- $1000 if score ≥ 0.7 (strong financials)

**Why These Weights?**
- Balance + Income = 80%: Core financial health indicators
- NSF = 20%: Significant but not sole disqualifier (gig workers may have temporary negatives)

---

### 3. Database Design

**Decision**: Use provided schema as-is (PostgreSQL)

**Tables:**
1. `bnpl_decision`: Immutable credit decisions
2. `bnpl_plan`: Repayment plans linked to decisions
3. `bnpl_installment`: Individual payment schedules
4. `outbound_webhook`: Retry queue for async webhooks

**Indexes:**
```sql
idx_decision_user_created ON (user_id, created_at DESC)
idx_plan_user_created ON (user_id, created_at DESC)
```
Optimizes `/decision/history` queries (most recent decisions first)

**Connection Pooling:**
- Pool size: 10 base + 10 overflow = 20 max
- `pool_pre_ping=True`: Detect stale connections
- `pool_recycle=3600`: Refresh connections hourly

---

### 4. Asynchronous Webhook Delivery

**Decision**: Background tasks with exponential backoff

**Why Async?**
- API response shouldn't wait for ledger (SLA decoupling)
- Ledger failures shouldn't block user approval

**Retry Strategy:**
```python
attempts = [1s, 2s, 4s, 8s, 16s]  # 5 retries max
backoff = base * (2 ** (attempt - 1))
```

**Tracking:**
- `outbound_webhook` table stores retry state
- Metrics: `webhook_latency_seconds`, `webhook_failures_total`

**Idempotency:**
- Each decision has unique UUID
- Ledger can deduplicate by `decision_id`

---

### 5. Observability Strategy

**Decision**: Prometheus metrics + structured JSON logs

**Metrics (Pull Model):**
```python
# Counters for approval rates
gerald_decision_total{outcome="approved|declined"}

# Distribution analysis
gerald_credit_limit_bucket{bucket="$0|$100|$400|$1000+"}

# Latency tracking
webhook_latency_seconds (histogram)
http_request_duration_seconds (histogram)

# Error monitoring
bank_fetch_failures_total
```

**Logs (Push Model):**
```json
{
  "timestamp": "2025-11-08T17:00:00Z",
  "level": "INFO",
  "request_id": "a1b2c3d4",
  "user_id": "user_good",
  "step": "decision_complete",
  "approval_outcome": "approved",
  "credit_limit_cents": 60000,
  "duration_ms": 234
}
```

**Why Both?**
- Metrics: Aggregate trends (approval rate over time)
- Logs: Individual request debugging (why was user X declined?)

---

### 6. Error Handling & Resilience

**HTTP Client Timeouts:**
```python
bank_client = httpx.AsyncClient(timeout=5.0)  # Fail fast
```

**Bank API Failures:**
- Timeout → Return 503 (Service Unavailable)
- Increment `bank_fetch_failures_total`
- Log with request ID for debugging

**Ledger Failures:**
- Non-blocking (background task)
- Retry with backoff
- If all retries fail → log error, mark webhook as failed
- Decision already persisted (not rolled back)

**Database Transactions:**
```python
try:
    db_decision = create_decision(...)
    db_plan = create_plan(...)
    db.commit()  # Atomic: both or neither
except:
    db.rollback()
    raise HTTPException(500)
```

---

### 7. Testing Strategy

**Unit Tests** (`tests/unit/`)
- Domain logic only (no I/O)
- Mock-free: pure function testing
- Coverage: scoring, installments, date utils

**Integration Tests** (`tests/integration/`)
- API endpoints with test database
- Mock external HTTP calls (bank, ledger)
- Verify persistence, error codes

**E2E Tests** (`tests/e2e/`)
- Real bank API integration (mock server)
- All 5 user personas
- Verify complete flows (decision → plan → history)

**Coverage Target:** 80%+

---

## 🚦 Request Flow

### POST /v1/decision Complete Flow

```
1. CLIENT REQUEST
   ↓
2. REQUEST ID MIDDLEWARE
   - Generate UUID
   - Attach to request.state
   ↓
3. METRICS MIDDLEWARE
   - Start timer
   ↓
4. ENDPOINT HANDLER (api/v1/decision.py)
   - Validate request body (Pydantic)
   ↓
5. FETCH TRANSACTIONS (infrastructure/clients/bank.py)
   - HTTP GET to bank API
   - Timeout: 5s
   - Parse JSON → Transaction objects
   ↓
6. RISK SCORING (domain/scoring.py)
   - analyze_transactions()
   - calculate_risk_score()
   - determine_credit_limit()
   ↓
7. PERSISTENCE (infrastructure/database/)
   - Create decision record
   - Create plan + installments (if approved)
   - db.commit() (atomic transaction)
   ↓
8. BACKGROUND WEBHOOK (infrastructure/clients/ledger.py)
   - FastAPI BackgroundTasks
   - POST to ledger with retry logic
   ↓
9. RESPONSE
   - Return JSON to client
   - Metrics recorded
   - Logs written
```

**Latency Budget:**
- Bank API: < 500ms
- Risk scoring: < 50ms
- DB write: < 100ms
- **Total**: < 1 second

---

## 📊 Data Flow

### Transaction Analysis Example

**Input:** 90 days of transactions
```json
[
  {"date": "2025-06-20", "balance_cents": 120000, ...},
  {"date": "2025-06-22", "balance_cents": 100000, ...},
  {"date": "2025-06-25", "balance_cents": 95000, ...}
]
```

**Processing:**
1. Sort by date
2. Build `balance_by_date` map
3. **Carry-forward** for missing days:
   - Jun 20: 120000
   - Jun 21: 120000 (carry)
   - Jun 22: 100000
   - Jun 23-24: 100000 (carry)
   - Jun 25: 95000

4. Calculate average: `sum(balances) / 90`

**Output:** `RiskFactors` object
```python
RiskFactors(
    avg_daily_balance_cents=85000,  # $850
    total_income_cents=900000,      # $9000
    total_spend_cents=750000,       # $7500
    income_spend_ratio=1.2,
    nsf_count=0,
    transaction_count=87,
    days_with_transactions=45
)
```

---

## 🔐 Security Considerations

### Current Implementation

1. **Database Credentials**
   - Environment variables (12-factor app)
   - Not committed to source control

2. **Docker Security**
   - Non-root user (`appuser`)
   - Minimal base image (Python slim)
   - No secrets in Dockerfile

3. **Input Validation**
   - Pydantic schemas enforce types
   - SQL injection prevented (SQLAlchemy ORM)

### Production Enhancements

1. **Authentication/Authorization**
   - JWT tokens or API keys
   - Rate limiting per user
   - RBAC for admin endpoints

2. **Secrets Management**
   - AWS Secrets Manager / HashiCorp Vault
   - Rotate DB passwords regularly

3. **Network Security**
   - TLS/HTTPS in production
   - Private VPC for database
   - WAF for API gateway

4. **PII Protection**
   - Hash/encrypt user_id in logs
   - GDPR compliance (right to erasure)

---

## 🎯 Performance Optimization

### Current Optimizations

1. **Database**
   - Connection pooling (reuse connections)
   - Indexes on `user_id` + `created_at`
   - Lazy loading relationships

2. **HTTP**
   - Async I/O (httpx)
   - Timeouts to prevent hanging
   - Connection reuse

3. **Caching Opportunities** (Future)
   - Redis for decision history
   - Cache user risk scores (TTL: 1 hour)

### Scalability

**Horizontal Scaling:**
- Stateless service (scales linearly)
- Deploy N instances behind load balancer
- PostgreSQL handles concurrent writes

**Database Bottlenecks:**
- Current: Single Postgres instance
- Future: Read replicas for `/history` queries
- Partitioning: `bnpl_decision` by month

**Metrics:**
- Current: ~100 req/sec per instance
- Bottleneck: Bank API latency (500ms)
- Target: 1000 req/sec with caching

---

## 🔄 Deployment Strategy

### CI/CD Pipeline (Recommended)

```yaml
1. Test Stage
   - pytest (unit + integration)
   - Coverage >80%
   - Linting (ruff, black)

2. Build Stage
   - Docker multi-stage build
   - Tag: {git-sha}

3. Deploy Stage
   - Blue/green deployment
   - Health check validation
   - Rollback on error

4. Monitor
   - Datadog APM
   - Prometheus alerts
   - PagerDuty escalation
```

### Infrastructure as Code

Provided:
- `terraform/monitors.tf`: Datadog alerts
- `docker-compose.yml`: Local development

Production:
- Kubernetes manifests (HPA, PDB)
- Terraform for RDS, VPC, ALB
- Helm charts for version management

---

## 📝 Future Enhancements

### Short Term (Sprint 1-2)

1. **OpenTelemetry Tracing**
   - Trace request across services
   - Visualize latency breakdown

2. **Database Migrations**
   - Alembic for schema changes
   - Versioned migrations

3. **API Versioning**
   - `/v2/decision` for breaking changes
   - Deprecation warnings

### Medium Term (Sprint 3-6)

1. **Machine Learning**
   - Replace rule-based scoring with ML model
   - A/B test new algorithms

2. **Event Streaming**
   - Kafka for decision events
   - Real-time analytics

3. **Multi-Region**
   - Deploy to multiple AWS regions
   - Database replication

---

## 🤔 Trade-offs & Limitations

### Current Limitations

1. **No Fraud Detection**
   - Assumes bank data is accurate
   - No velocity checks (multiple applications)

2. **Synchronous Bank API Call**
   - Blocks until transactions fetched
   - Could use cached data for faster response

3. **Single Transaction Source**
   - Relies only on one bank account
   - Could aggregate multiple accounts

### Considered Alternatives

**Alternative 1:** Event-Driven Architecture
- Pro: Better decoupling
- Con: Over-engineered for 8-hour challenge
- Decision: Use simple HTTP + webhooks

**Alternative 2:** ML-Based Scoring
- Pro: More accurate over time
- Con: Requires training data, explainability issues
- Decision: Use transparent rule-based system

**Alternative 3:** NoSQL Database
- Pro: Flexible schema
- Con: Provided SQL schema, ACID needed for transactions
- Decision: Use PostgreSQL as specified

---

## 📚 References

- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/)
- [Prometheus Metrics](https://prometheus.io/docs/practices/naming/)
- [12-Factor App](https://12factor.net/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-08
**Author:** Gerald Engineering Team
