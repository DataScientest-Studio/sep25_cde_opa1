#!/bin/bash
# Main startup script for the entire cryptocurrency API stack

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     Cryptocurrency Data API - Full Stack Deployment            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found"
    if [ -f .env.example ]; then
        echo "📝 Creating .env from .env.example..."
        cp .env.example .env
        echo "✓ .env file created"
        echo ""
        echo "⚠️  Please review and update the .env file with your settings,"
        echo "   then run this script again."
        exit 0
    else
        echo "❌ No .env.example file found. Cannot create .env"
        exit 1
    fi
fi

echo "✓ .env file exists"
echo ""

# Ask if user wants to populate data
echo "Do you want to populate historical data on startup?"
echo "(This will fetch 2 years of data from Binance for BTC, ETH, SOL)"
read -p "Populate data? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    export POPULATE_DATA=true
    echo "✓ Data will be populated automatically"
else
    export POPULATE_DATA=false
    echo "ℹ Data population skipped (you can run 'python src/main.py' later)"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "Starting services..."
echo "════════════════════════════════════════════════════════════════"
echo ""

# Stop any existing containers
echo "Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Build and start services
echo ""
echo "Building and starting services..."
echo ""
docker-compose up -d --build

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "Waiting for services to be healthy..."
echo "════════════════════════════════════════════════════════════════"
echo ""

# Wait for services to be healthy
max_wait=120
elapsed=0
interval=5

while [ $elapsed -lt $max_wait ]; do
    mongo_health=$(docker inspect --format='{{.State.Health.Status}}' sep25_opa1_mongo 2>/dev/null || echo "starting")
    postgres_health=$(docker inspect --format='{{.State.Health.Status}}' sep25_opa1_postgres 2>/dev/null || echo "starting")
    api_health=$(docker inspect --format='{{.State.Health.Status}}' sep25_opa1_api 2>/dev/null || echo "starting")

    echo "MongoDB: $mongo_health | PostgreSQL: $postgres_health | API: $api_health"

    if [ "$mongo_health" = "healthy" ] && [ "$postgres_health" = "healthy" ] && [ "$api_health" = "healthy" ]; then
        echo ""
        echo "✓ All services are healthy!"
        break
    fi

    sleep $interval
    elapsed=$((elapsed + interval))
done

if [ $elapsed -ge $max_wait ]; then
    echo ""
    echo "⚠️  Services took longer than expected to start"
    echo "   Check the logs with: docker-compose logs"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "Deployment Summary"
echo "════════════════════════════════════════════════════════════════"
echo ""
docker-compose ps
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ Stack is running!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Services available at:"
echo "  🌐 API:              http://localhost:8000"
echo "  📚 API Docs:         http://localhost:8000/docs"
echo "  💾 MongoDB:          localhost:27025"
echo "  🐘 PostgreSQL:       localhost:5435"
echo "  🔧 PgAdmin:          http://localhost:5436"
echo ""
echo "Useful commands:"
echo "  View logs:           docker-compose logs -f"
echo "  View API logs:       docker-compose logs -f api"
echo "  Stop all:            docker-compose down"
echo "  Restart API:         docker-compose restart api"
echo ""
echo "To populate data manually (if not done automatically):"
echo "  docker-compose exec api python src/main.py"
echo ""
echo "════════════════════════════════════════════════════════════════"

