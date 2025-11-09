# Quick Start Guide

## ✅ Services Are Running

Your mock services are already up and running:
- ✅ Bank API: http://localhost:8001
- ✅ Ledger API: http://localhost:8002
- ✅ PostgreSQL: localhost:5432

## 🚀 Next Steps

### 1. Configure Environment

```bash
cd /home/roberto/geraldChallenge/gerald_bnpl_assets/gerald_bnpl_assets/gerald-gateway
cp .env.example .env
```

The defaults work with Docker services!

### 2. Run Tests

```bash
# Run all tests
PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring poetry run pytest -v

# Run with coverage
PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring poetry run pytest --cov=gerald_gateway
```

### 3. Start the Service

```bash
PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring poetry run uvicorn gerald_gateway.api.main:app --reload --port 8000
```

### 4. Test the API (in another terminal)

```bash
# Health check
curl http://localhost:8000/health

# Test user_good (should approve)
curl -X POST http://localhost:8000/v1/decision \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_good", "amount_cents_requested": 40000}' | jq

# Test user_overdraft (should decline)
curl -X POST http://localhost:8000/v1/decision \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_overdraft", "amount_cents_requested": 40000}' | jq

# Get plan (replace with actual plan_id from above)
curl http://localhost:8000/v1/plan/{plan_id} | jq

# Get decision history
curl "http://localhost:8000/v1/decision/history?user_id=user_good" | jq

# View metrics
curl http://localhost:8000/metrics | grep gerald

# API Documentation
open http://localhost:8000/docs
```

## 🐳 Alternative: Run Everything in Docker

```bash
cd /home/roberto/geraldChallenge/gerald_bnpl_assets/gerald_bnpl_assets
docker-compose up --build gateway

# Test
curl -X POST http://localhost:8000/v1/decision \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_good", "amount_cents_requested": 40000}'
```

## 🧪 Test All 5 User Personas

```bash
# user_good: Strong financials → Should approve with high limit
curl -X POST http://localhost:8000/v1/decision \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_good", "amount_cents_requested": 40000}' | jq '.approved, .credit_limit_cents'

# user_overdraft: NSF history → Should decline or low limit
curl -X POST http://localhost:8000/v1/decision \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_overdraft", "amount_cents_requested": 40000}' | jq '.approved, .credit_limit_cents'

# user_thin: Limited history → Conservative approval
curl -X POST http://localhost:8000/v1/decision \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_thin", "amount_cents_requested": 40000}' | jq '.approved, .credit_limit_cents'

# user_gig: Irregular income → Moderate approval
curl -X POST http://localhost:8000/v1/decision \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_gig", "amount_cents_requested": 30000}' | jq '.approved, .credit_limit_cents'

# user_highutil: High spending → Granted amount capped to limit
curl -X POST http://localhost:8000/v1/decision \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_highutil", "amount_cents_requested": 100000}' | jq '.approved, .credit_limit_cents, .amount_granted_cents'
```

## 📊 View Logs & Metrics

```bash
# View structured JSON logs
docker-compose logs -f gateway

# Prometheus metrics
curl http://localhost:8000/metrics

# Filter for gerald metrics
curl http://localhost:8000/metrics | grep gerald
```

## 🔧 Troubleshooting

### Poetry Keyring Error

If you get keyring errors, always prefix commands with:
```bash
PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring
```

Or export it:
```bash
export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring
```

### Services Not Running

```bash
# Check status
docker-compose ps

# Restart services
docker-compose restart

# View logs
docker-compose logs bank
docker-compose logs ledger
docker-compose logs postgres
```

### Database Issues

```bash
# Recreate database
docker-compose down -v  # Remove volumes
docker-compose up -d postgres

# Check schema loaded
docker-compose exec postgres psql -U postgres -d gerald -c "\dt"
```

## 📁 Project Structure

```
gerald-gateway/
├── gerald_gateway/
│   ├── api/              # FastAPI endpoints
│   ├── domain/           # Business logic (risk scoring)
│   ├── infrastructure/   # DB, HTTP clients, metrics
│   └── config.py         # Settings
├── tests/
│   ├── unit/             # Domain logic tests
│   ├── integration/      # API tests
│   └── e2e/              # User persona tests
├── pyproject.toml        # Poetry dependencies
└── README.md             # Full documentation
```

---

**Ready to code! 🎯**
