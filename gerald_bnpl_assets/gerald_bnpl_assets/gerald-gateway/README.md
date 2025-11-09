# Gerald BNPL Gateway

Production-grade microservice for Buy Now, Pay Later (BNPL) credit decisions and repayment plan management.

---

## 🎬 Video Walkthrough

[![Watch the demonstration](https://cdn.loom.com/sessions/thumbnails/6991c2cce2a94d2ea753a1dbbb0e2abf-with-play.gif)](https://www.loom.com/share/6991c2cce2a94d2ea753a1dbbb0e2abf)

**[▶️ Click to watch the full architecture and demo walkthrough](https://www.loom.com/share/6991c2cce2a94d2ea753a1dbbb0e2abf)**

This video demonstrates:
- Service architecture and design decisions
- All 5 user personas (user_good, user_overdraft, user_thin, user_gig, user_highutil)
- Risk scoring algorithm in action
- Metrics, logging, and observability features
- Webhook retry logic and error handling

---

## 🏗️ Architecture

**Clean Architecture** with three layers:
- **API Layer**: FastAPI endpoints, request/response validation
- **Domain Layer**: Pure business logic (risk scoring, installment generation)
- **Infrastructure Layer**: External integrations (PostgreSQL, Bank API, Ledger webhooks, metrics)

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design decisions.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Docker & Docker Compose
- PostgreSQL 15+ (or use Docker)

### 1. Start Mock Services

```bash
# From project root (gerald_bnpl_assets)
docker-compose up -d bank ledger postgres

# Verify services
curl http://localhost:8001/bank/transactions?user_id=user_good
curl http://localhost:8002/health
```

### 2. Setup Development Environment

```bash
cd gerald-gateway

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Edit .env if needed (defaults work with Docker)

# Activate virtual environment
poetry shell
```

### 3. Initialize Database

```bash
# Schema is auto-loaded via docker-compose
# Or manually:
psql postgresql://postgres:postgres@localhost:5432/gerald -f ../db/schema.sql
```

### 4. Run Service

```bash
# Development mode with auto-reload
uvicorn gerald_gateway.api.main:app --reload --port 8000

# Or use Docker
docker-compose up gateway
```

### 5. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Make a credit decision
curl -X POST http://localhost:8000/v1/decision \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_good", "amount_cents_requested": 40000}'

# Get repayment plan
curl http://localhost:8000/v1/plan/{plan_id}

# View decision history
curl "http://localhost:8000/v1/decision/history?user_id=user_good"

# Prometheus metrics
curl http://localhost:8000/metrics
```

---

## 🧪 Testing

```bash
# Run all tests with coverage
poetry run pytest

# Unit tests only
poetry run pytest tests/unit/

# Integration tests (requires mock servers)
docker-compose up -d bank ledger postgres
poetry run pytest tests/integration/

# E2E tests with real user personas
poetry run pytest tests/e2e/ -v

# Coverage report
poetry run pytest --cov-report=html
open htmlcov/index.html
```

---

## 📊 API Endpoints

### POST /v1/decision
Make BNPL credit decision.

**Request:**
```json
{
  "user_id": "user_good",
  "amount_cents_requested": 40000
}
```

**Response (Approved):**
```json
{
  "approved": true,
  "credit_limit_cents": 60000,
  "amount_granted_cents": 40000,
  "plan_id": "8a7f3d91-..."
}
```

**Response (Declined):**
```json
{
  "approved": false,
  "credit_limit_cents": 0,
  "amount_granted_cents": 0,
  "plan_id": null
}
```

### GET /v1/plan/{plan_id}
Retrieve repayment schedule.

**Response:**
```json
{
  "plan_id": "8a7f3d91-...",
  "user_id": "user_good",
  "total_cents": 40000,
  "installments": [
    {"due_date": "2025-11-22", "amount_cents": 10000, "status": "scheduled"},
    {"due_date": "2025-12-06", "amount_cents": 10000, "status": "scheduled"},
    {"due_date": "2025-12-20", "amount_cents": 10000, "status": "scheduled"},
    {"due_date": "2026-01-03", "amount_cents": 10000, "status": "scheduled"}
  ],
  "created_at": "2025-11-08T17:00:00Z"
}
```

### GET /v1/decision/history?user_id={user_id}
Fetch recent decisions for a user.

---

## 🎯 Risk Scoring Algorithm

### Metrics Analyzed
1. **Average Daily Balance** (carry-forward for no-transaction days)
2. **Income vs Spend Ratio** (credits / debits)
3. **NSF/Overdraft Count** (nsf flag OR negative balance)

### Scoring Formula

```python
score = (0.4 × balance_score) + (0.4 × income_score) + (0.2 × nsf_score)

balance_score = min(avg_balance / $1000, 1.0)
income_score = min(income_ratio, 1.0)
nsf_score = 1.0 if nsf_count == 0 else 0.0
```

### Credit Limit Buckets

| Score Range | Credit Limit | Risk Band |
|-------------|--------------|-----------|
| 0.0 - 0.2   | $0 (decline) | high_risk |
| 0.2 - 0.4   | $100         | moderate_risk |
| 0.4 - 0.7   | $400         | acceptable_risk |
| 0.7 - 1.0   | $1000        | low_risk |

**Rationale:**
- $1000 avg balance = financial stability baseline
- Income > Spend = living within means
- Any NSF = major red flag (20% penalty)

---

## 📈 Observability

### Metrics (Prometheus)

```python
# Decision outcomes
gerald_decision_total{outcome="approved|declined"}

# Credit limit distribution
gerald_credit_limit_bucket{bucket="$0|$0-$100|$100-$400|$400+"}

# Webhook performance
webhook_latency_seconds (histogram)
webhook_failures_total

# Bank API health
bank_fetch_failures_total

# HTTP request latency
http_request_duration_seconds{method, endpoint, status}
```

### Structured Logging

All logs output as JSON with:
- `timestamp`: ISO8601
- `request_id`: UUID for tracing
- `user_id`: User identifier
- `step`: Operation stage
- `duration_ms`: Latency
- `approval_outcome`: Decision result

### Alerts (Terraform Config Provided)

- Error rate > 2% over 5 min → PagerDuty
- Approval rate drops >20% vs 24h baseline → PagerDuty

---

## 🔧 Configuration

Environment variables (`.env`):

```bash
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/gerald
BANK_API_BASE=http://localhost:8001
LEDGER_WEBHOOK_URL=http://localhost:8002/mock-ledger
SERVICE_NAME=gerald-gateway
LOG_LEVEL=INFO
HTTP_TIMEOUT_SECONDS=5.0
WEBHOOK_MAX_RETRIES=5
WEBHOOK_BACKOFF_BASE=1.0
```

---

## 🐳 Docker Deployment

```bash
# Build and run entire stack
docker-compose up --build

# Services:
# - gerald-gateway: http://localhost:8000
# - postgres: localhost:5432
# - bank (mock): http://localhost:8001
# - ledger (mock): http://localhost:8002

# View logs
docker-compose logs -f gateway

# Stop all services
docker-compose down
```

---

## 📁 Project Structure

```
gerald-gateway/
├── gerald_gateway/
│   ├── api/              # FastAPI endpoints
│   │   ├── main.py       # App factory
│   │   ├── middleware.py # Request ID, metrics
│   │   └── v1/           # API v1 routes
│   ├── domain/           # Business logic
│   │   ├── scoring.py    # Risk algorithm
│   │   └── installments.py
│   ├── infrastructure/   # External integrations
│   │   ├── database/     # SQLAlchemy models
│   │   ├── clients/      # HTTP clients
│   │   └── observability/ # Metrics, logging
│   └── config.py         # Pydantic Settings
├── tests/
│   ├── unit/             # Domain logic tests
│   ├── integration/      # API tests
│   └── e2e/              # User persona tests
├── pyproject.toml        # Poetry dependencies
└── Dockerfile            # Multi-stage build
```

---

## 👥 User Personas (Test Data)

| User | Profile | Expected Outcome |
|------|---------|------------------|
| `user_good` | Strong financials | ✅ Approve, high limit ($600-$1000) |
| `user_overdraft` | NSF history | ❌ Decline or very low limit |
| `user_thin` | Limited history | ⚠️ Conservative (decline or $100) |
| `user_gig` | Irregular income | ⚠️ Moderate approval |
| `user_highutil` | High spending | ✅ Approve but cap at limit |

---

## 🎬 Loom Video

**See the video walkthrough at the top of this README** or [click here to watch](https://www.loom.com/share/6991c2cce2a94d2ea753a1dbbb0e2abf).

The video covers:
1. Architecture overview
2. Code structure explanation
3. Running all 5 test personas
4. Metrics and logging in action
5. Webhook retry logic
6. Error handling scenarios

---

## 📝 Development Notes

### Code Quality
- Type hints throughout
- 80%+ test coverage
- Black formatting (line length 100)
- Ruff linting

### Production Readiness
- ✅ Connection pooling (10 connections, 1h recycle)
- ✅ Graceful DB session cleanup
- ✅ Exponential backoff webhooks
- ✅ Request ID tracing
- ✅ Health checks
- ✅ Prometheus metrics endpoint
- ✅ Multi-stage Docker build
- ✅ Non-root container user

---

## 🤝 Contributing

This is a take-home challenge submission. For production use:
1. Add authentication/authorization
2. Implement rate limiting
3. Add OpenTelemetry distributed tracing
4. Set up Datadog/Prometheus dashboards
5. Configure CI/CD pipelines
6. Add database migrations (Alembic)

---

## 📄 License

MIT License - Gerald Engineering Team
