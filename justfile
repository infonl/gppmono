# GPP Monorepo - Development Commands
# Run 'just' or 'just help' to see available commands

# Default recipe: show help
default:
    @just --list --unsorted

# =============================================================================
# MAIN COMMANDS
# =============================================================================

# Start all services (full stack)
up *ARGS:
    docker compose up {{ARGS}}

# Start all services in background
up-d:
    docker compose up -d

# Stop all services
down:
    docker compose down

# Stop all services and remove volumes (clean slate)
down-v:
    docker compose down -v

# Restart all services
restart:
    docker compose restart

# =============================================================================
# SELECTIVE STARTUP
# =============================================================================

# Start only infrastructure (postgres, redis)
up-infra:
    docker compose up -d postgres redis
    @echo "Waiting for postgres to be healthy..."
    @until docker compose exec postgres pg_isready -U postgres > /dev/null 2>&1; do sleep 1; done
    @echo "Infrastructure ready!"

# Start dependencies (infra + openzaak + publicatiebank)
up-deps:
    docker compose up -d postgres redis openzaak openzaak-celery publicatiebank publicatiebank-celery
    @echo "Waiting for services to be healthy..."
    @sleep 5
    @just health-deps

# Start woo-hoo service only
up-woo-hoo:
    docker compose up -d woo-hoo

# Start gpp-app only (requires deps to be running)
up-gpp-app:
    docker compose up -d gpp-app

# =============================================================================
# DEVELOPMENT MODE
# =============================================================================

# Run Vue frontend dev server with hot reload (for gpp-app development)
dev-frontend:
    cd services/gpp-app/odpc.client && npm install && npm run dev

# Run .NET backend locally (for debugging)
dev-backend:
    cd services/gpp-app && dotnet run --project ODPC.Server --launch-profile http

# Run woo-hoo locally with hot reload (for development)
dev-woo-hoo:
    cd services/woo-hoo && uv run uvicorn woo_hoo.main:app --host 0.0.0.0 --port 8003 --reload

# Full development setup: deps in Docker, frontends running locally
dev:
    @echo "Starting dependencies in Docker..."
    just up-deps
    @echo ""
    @echo "Dependencies started. Now run in separate terminals:"
    @echo "  just dev-frontend    # Vue dev server (port 5173)"
    @echo "  just dev-backend     # .NET backend (optional, or use Docker)"
    @echo "  just dev-woo-hoo     # woo-hoo service (port 8003)"
    @echo ""
    @echo "Or for full Docker stack: just up"

# =============================================================================
# LOGS & MONITORING
# =============================================================================

# Show logs from all services
logs *ARGS:
    docker compose logs -f {{ARGS}}

# Show logs from specific service
logs-gpp-app:
    docker compose logs -f gpp-app

logs-publicatiebank:
    docker compose logs -f publicatiebank publicatiebank-celery

logs-woo-hoo:
    docker compose logs -f woo-hoo

logs-openzaak:
    docker compose logs -f openzaak openzaak-celery

# =============================================================================
# HEALTH CHECKS
# =============================================================================

# Check health of all services
health:
    @echo "=== GPP Services Health Check ==="
    @echo ""
    @echo "1. PostgreSQL:"
    @docker compose exec postgres pg_isready -U postgres > /dev/null 2>&1 && echo "   ✓ Healthy" || echo "   ✗ Not ready"
    @echo ""
    @echo "2. Redis:"
    @docker compose exec redis redis-cli ping > /dev/null 2>&1 && echo "   ✓ Healthy" || echo "   ✗ Not ready"
    @echo ""
    @echo "3. OpenZaak (port 8001):"
    @curl -sf http://localhost:8001/ > /dev/null 2>&1 && echo "   ✓ Healthy" || echo "   ✗ Not responding"
    @echo ""
    @echo "4. GPP-Publicatiebank (port 8002):"
    @curl -sf http://localhost:8002/ > /dev/null 2>&1 && echo "   ✓ Healthy" || echo "   ✗ Not responding"
    @echo ""
    @echo "5. woo-hoo (port 8003):"
    @curl -sf http://localhost:8003/health > /dev/null 2>&1 && echo "   ✓ Healthy" || echo "   ✗ Not responding"
    @echo ""
    @echo "6. GPP-App (port 62230):"
    @curl -sf http://localhost:62230/api/me > /dev/null 2>&1 && echo "   ✓ Healthy" || echo "   ✗ Not responding"
    @echo ""
    @echo "7. Nginx proxy (port 8080):"
    @curl -sf http://localhost:8080/nginx-health > /dev/null 2>&1 && echo "   ✓ Healthy" || echo "   ✗ Not responding"
    @echo ""
    @echo "=== Access URLs ==="
    @echo "Main app:           http://localhost:8080"
    @echo "GPP-App direct:     http://localhost:62230"
    @echo "Publicatiebank:     http://localhost:8002/admin (admin/admin)"
    @echo "OpenZaak:           http://localhost:8001/admin (admin/admin)"
    @echo "woo-hoo API docs:   http://localhost:8003/docs"
    @echo ""

# Check health of dependencies only
health-deps:
    @echo "Checking dependency health..."
    @docker compose exec postgres pg_isready -U postgres > /dev/null 2>&1 && echo "✓ PostgreSQL ready" || echo "✗ PostgreSQL not ready"
    @docker compose exec redis redis-cli ping > /dev/null 2>&1 && echo "✓ Redis ready" || echo "✗ Redis not ready"
    @curl -sf http://localhost:8002/ > /dev/null 2>&1 && echo "✓ Publicatiebank ready" || echo "✗ Publicatiebank not ready"

# =============================================================================
# DATABASE
# =============================================================================

# Open psql shell to postgres
db-shell:
    docker compose exec postgres psql -U postgres

# Connect to ODPC database
db-odpc:
    docker compose exec postgres psql -U postgres -d ODPC

# Connect to woo_publications database
db-publicatiebank:
    docker compose exec postgres psql -U postgres -d woo_publications

# Connect to openzaak database
db-openzaak:
    docker compose exec postgres psql -U postgres -d openzaak

# Run migrations for gpp-app
migrate-gpp-app:
    docker compose exec gpp-app dotnet ef database update --project /app/ODPC.Server

# =============================================================================
# TESTING
# =============================================================================

# Run all tests
test: test-gpp-app test-woo-hoo

# Run gpp-app tests
test-gpp-app:
    cd services/gpp-app && dotnet test ODPC.Test

# Run gpp-app frontend tests
test-gpp-app-frontend:
    cd services/gpp-app/odpc.client && npm install && npm run test

# Run woo-hoo tests
test-woo-hoo:
    cd services/woo-hoo && uv run pytest

# Run woo-hoo tests with coverage
test-woo-hoo-cov:
    cd services/woo-hoo && uv run pytest --cov=woo_hoo --cov-report=term-missing

# =============================================================================
# BUILD & LINT
# =============================================================================

# Build all Docker images
build:
    docker compose build

# Build specific service
build-gpp-app:
    docker compose build gpp-app

build-woo-hoo:
    docker compose build woo-hoo

# Lint all code
lint: lint-gpp-app lint-woo-hoo

# Lint gpp-app
lint-gpp-app:
    cd services/gpp-app && dotnet format ODPC.sln --verify-no-changes
    cd services/gpp-app/odpc.client && npm run lint

# Lint woo-hoo
lint-woo-hoo:
    cd services/woo-hoo && uv run ruff check .

# Format all code
format: format-gpp-app format-woo-hoo

# Format gpp-app
format-gpp-app:
    cd services/gpp-app && dotnet format ODPC.sln
    cd services/gpp-app/odpc.client && npm run format

# Format woo-hoo
format-woo-hoo:
    cd services/woo-hoo && uv run ruff format .

# =============================================================================
# UTILITIES
# =============================================================================

# Install frontend dependencies
install-frontend:
    cd services/gpp-app/odpc.client && npm install

# Install woo-hoo dependencies
install-woo-hoo:
    cd services/woo-hoo && uv sync

# Clean up Docker resources
clean:
    docker compose down -v --remove-orphans
    docker system prune -f

# Show running containers
ps:
    docker compose ps

# Execute command in service container
exec service *ARGS:
    docker compose exec {{service}} {{ARGS}}

# Pull latest images
pull:
    docker compose pull

# Copy .env.example to .env if it doesn't exist
setup-env:
    @if [ ! -f .env ]; then cp .env.example .env && echo "Created .env from .env.example - please edit it!"; else echo ".env already exists"; fi

# =============================================================================
# FIXTURES & SEED DATA
# =============================================================================

# Load fixtures into publicatiebank
load-fixtures:
    docker compose exec publicatiebank python /app/src/manage.py loaddata /app/fixtures/*.json

# Create a test user group in gpp-app (for testing without OIDC)
seed-test-data:
    @echo "Creating test data..."
    @echo "Note: This creates test user groups and sample data for local development"
    @docker compose exec gpp-app dotnet /app/publish/ODPC.dll --seed-test-data || echo "Seed data command not available - data may need manual setup"

# =============================================================================
# QUICK START
# =============================================================================

# First-time setup: create .env, build, and start
quickstart:
    @echo "=== GPP Monorepo Quick Start ==="
    @just setup-env
    @echo ""
    @echo "Building images (this may take a while)..."
    @just build
    @echo ""
    @echo "Starting services..."
    @just up-d
    @echo ""
    @echo "Waiting for services to be ready..."
    @sleep 30
    @just health
    @echo ""
    @echo "=== Quick Start Complete ==="
    @echo ""
    @echo "NOTE: You need to set OPENROUTER_API_KEY in .env for woo-hoo to work!"
    @echo "Get a key at: https://openrouter.ai"
