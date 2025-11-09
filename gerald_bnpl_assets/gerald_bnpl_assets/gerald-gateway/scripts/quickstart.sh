#!/bin/bash
set -e

echo "🚀 Gerald BNPL Gateway - Quick Start"
echo "===================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is running"

# Start mock services
echo "📦 Starting mock services (bank, ledger, postgres)..."
cd ..
docker-compose up -d bank ledger postgres

echo "⏳ Waiting for services to be ready..."
sleep 5

# Check services
echo "🔍 Verifying services..."
curl -s http://localhost:8001/health > /dev/null && echo "✅ Bank server ready" || echo "❌ Bank server not ready"
curl -s http://localhost:8002/health > /dev/null && echo "✅ Ledger server ready" || echo "❌ Ledger server not ready"

# Install dependencies
echo "📚 Installing Python dependencies..."
cd gerald-gateway
poetry install --no-root

# Copy env file
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Run tests:"
echo "   poetry run pytest"
echo ""
echo "2. Start the service:"
echo "   poetry run uvicorn gerald_gateway.api.main:app --reload"
echo ""
echo "3. Test the API:"
echo "   curl -X POST http://localhost:8000/v1/decision \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"user_id\": \"user_good\", \"amount_cents_requested\": 40000}'"
echo ""
echo "4. View docs:"
echo "   Open http://localhost:8000/docs"
echo ""
echo "5. View metrics:"
echo "   curl http://localhost:8000/metrics"
