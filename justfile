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

# Load fixtures into OpenZaak (catalogi for document types)
load-openzaak-fixtures:
    docker compose exec openzaak-web python /app/src/manage.py loaddata /app/fixtures/*.json

# Seed local dev data (user groups, permissions) - runs automatically in 'just local'
seed-local-dev:
    #!/usr/bin/env bash
    echo "Seeding local development data..."

    # Wait for gpp-app to be healthy (ensures migrations have run)
    for i in {1..30}; do
        if curl -sf http://localhost:62230/api/me > /dev/null 2>&1; then
            break
        fi
        sleep 2
    done

    # 1. Create user group and link local-dev user
    docker compose exec -T postgres psql -U postgres -d ODPC -c "
        INSERT INTO \"Gebruikersgroepen\" (\"Uuid\", \"Naam\", \"Omschrijving\")
        VALUES ('d3da5277-ea07-4921-97b8-e9a181390c76', 'Local Dev Group', 'Default group for local development')
        ON CONFLICT (\"Uuid\") DO NOTHING;
        INSERT INTO \"GebruikersgroepGebruikers\" (\"GebruikersgroepUuid\", \"GebruikerId\")
        VALUES ('d3da5277-ea07-4921-97b8-e9a181390c76', 'local-dev')
        ON CONFLICT DO NOTHING;
    " 2>/dev/null || true
    echo "  ✓ User 'local-dev' linked to 'Local Dev Group'"

    # 2. Enable test organisation in publicatiebank
    docker compose exec -T postgres psql -U postgres -d woo_publications -c "
        UPDATE metadata_organisation SET is_actief = true
        WHERE uuid = '5e1e724c-c3ea-4d0a-aa79-d0b66aefe27c';
    " 2>/dev/null || true
    echo "  ✓ Enabled test organisation 'gemeente Appingedam'"

    # 3. Add waardelijsten permissions (organisation + information categories)
    docker compose exec -T postgres psql -U postgres -d ODPC -c "
        INSERT INTO \"GebruikersgroepWaardelijsten\" (\"GebruikersgroepUuid\", \"WaardelijstId\")
        VALUES
            ('d3da5277-ea07-4921-97b8-e9a181390c76', '5e1e724c-c3ea-4d0a-aa79-d0b66aefe27c'),
            ('d3da5277-ea07-4921-97b8-e9a181390c76', 'be4e21c2-0be5-4616-945e-1f101b0c0e6d'),
            ('d3da5277-ea07-4921-97b8-e9a181390c76', '8f3bdef0-a926-4f67-b1f2-94c583c462ce'),
            ('d3da5277-ea07-4921-97b8-e9a181390c76', '88fb1c5e-e899-456d-b077-6101a9829c11'),
            ('d3da5277-ea07-4921-97b8-e9a181390c76', '9aeb7501-3f77-4f36-8c8f-d21f47c2d6e8'),
            ('d3da5277-ea07-4921-97b8-e9a181390c76', 'b84c3b0d-a471-48f5-915f-7fbd8b94188f')
        ON CONFLICT DO NOTHING;
    " 2>/dev/null || true
    echo "  ✓ Added publication permissions"

    echo ""
    echo "✓ Local dev data seeded successfully"

# =============================================================================
# LOCAL DEVELOPMENT - SINGLE COMMAND
# =============================================================================

# Start entire stack for local development (the main command you'll use)
local *ARGS:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "=== GPP Local Development ==="
    echo ""

    # Ensure .env exists
    if [ ! -f .env ]; then
        echo "Creating .env from .env.example..."
        cp .env.example .env
        echo "⚠️  Created .env - you may need to add OPENROUTER_API_KEY"
        echo ""
    fi

    # Check for OPENROUTER_API_KEY
    if grep -q "^OPENROUTER_API_KEY=$" .env 2>/dev/null || ! grep -q "^OPENROUTER_API_KEY=" .env 2>/dev/null; then
        echo "⚠️  Warning: OPENROUTER_API_KEY not set in .env"
        echo "   woo-hoo LLM features won't work without it"
        echo "   Get a key at: https://openrouter.ai/keys"
        echo ""
    fi

    # Build if images don't exist
    if ! docker images | grep -q "gppmono-gpp-app" 2>/dev/null; then
        echo "Building Docker images (first run, this takes a while)..."
        docker compose build
        echo ""
    fi

    # Start everything
    echo "Starting all services..."
    docker compose up -d {{ARGS}}

    echo ""
    echo "Waiting for services to be healthy..."

    # Wait for postgres
    echo -n "  PostgreSQL: "
    for i in {1..30}; do
        if docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
            echo "✓"
            break
        fi
        sleep 1
        if [ $i -eq 30 ]; then echo "✗ (timeout)"; fi
    done

    # Wait for redis
    echo -n "  Redis: "
    for i in {1..10}; do
        if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
            echo "✓"
            break
        fi
        sleep 1
        if [ $i -eq 10 ]; then echo "✗ (timeout)"; fi
    done

    # Wait for openzaak
    echo -n "  OpenZaak: "
    for i in {1..60}; do
        if curl -sf http://localhost:8001/ > /dev/null 2>&1; then
            echo "✓"
            break
        fi
        sleep 2
        if [ $i -eq 60 ]; then echo "✗ (timeout)"; fi
    done

    # Wait for publicatiebank
    echo -n "  Publicatiebank: "
    for i in {1..60}; do
        if curl -sf http://localhost:8002/ > /dev/null 2>&1; then
            echo "✓"
            break
        fi
        sleep 2
        if [ $i -eq 60 ]; then echo "✗ (timeout)"; fi
    done

    # Wait for gpp-app
    echo -n "  GPP-App: "
    for i in {1..60}; do
        if curl -sf http://localhost:62230/api/me > /dev/null 2>&1; then
            echo "✓"
            break
        fi
        sleep 2
        if [ $i -eq 60 ]; then echo "✗ (timeout)"; fi
    done

    # Wait for woo-hoo
    echo -n "  woo-hoo: "
    for i in {1..30}; do
        if curl -sf http://localhost:8003/health > /dev/null 2>&1; then
            echo "✓"
            break
        fi
        sleep 1
        if [ $i -eq 30 ]; then echo "✗ (timeout)"; fi
    done

    # Seed local dev data (user groups, permissions, etc.)
    echo ""
    echo "Seeding local development data..."

    # 1. Create user group and link local-dev user
    docker compose exec -T postgres psql -U postgres -d ODPC -c "
        INSERT INTO \"Gebruikersgroepen\" (\"Uuid\", \"Naam\", \"Omschrijving\")
        VALUES ('d3da5277-ea07-4921-97b8-e9a181390c76', 'Local Dev Group', 'Default group for local development')
        ON CONFLICT (\"Uuid\") DO NOTHING;
        INSERT INTO \"GebruikersgroepGebruikers\" (\"GebruikersgroepUuid\", \"GebruikerId\")
        VALUES ('d3da5277-ea07-4921-97b8-e9a181390c76', 'local-dev')
        ON CONFLICT DO NOTHING;
    " > /dev/null 2>&1 || true
    echo "  ✓ User 'local-dev' linked to 'Local Dev Group'"

    # 2. Enable a test organisation in publicatiebank
    docker compose exec -T postgres psql -U postgres -d woo_publications -c "
        UPDATE metadata_organisation SET is_actief = true
        WHERE uuid = '5e1e724c-c3ea-4d0a-aa79-d0b66aefe27c';
    " > /dev/null 2>&1 || true
    echo "  ✓ Enabled test organisation 'gemeente Appingedam'"

    # 3. Add waardelijsten permissions (organisation + information categories)
    docker compose exec -T postgres psql -U postgres -d ODPC -c "
        INSERT INTO \"GebruikersgroepWaardelijsten\" (\"GebruikersgroepUuid\", \"WaardelijstId\")
        VALUES
            ('d3da5277-ea07-4921-97b8-e9a181390c76', '5e1e724c-c3ea-4d0a-aa79-d0b66aefe27c'),
            ('d3da5277-ea07-4921-97b8-e9a181390c76', 'be4e21c2-0be5-4616-945e-1f101b0c0e6d'),
            ('d3da5277-ea07-4921-97b8-e9a181390c76', '8f3bdef0-a926-4f67-b1f2-94c583c462ce'),
            ('d3da5277-ea07-4921-97b8-e9a181390c76', '88fb1c5e-e899-456d-b077-6101a9829c11'),
            ('d3da5277-ea07-4921-97b8-e9a181390c76', '9aeb7501-3f77-4f36-8c8f-d21f47c2d6e8'),
            ('d3da5277-ea07-4921-97b8-e9a181390c76', 'b84c3b0d-a471-48f5-915f-7fbd8b94188f')
        ON CONFLICT DO NOTHING;
    " > /dev/null 2>&1 || true
    echo "  ✓ Added publication permissions (organisation + 5 information categories)"

    # 4. Load OpenZaak fixtures (catalogi for document types)
    docker compose exec -T openzaak-web python /app/src/manage.py loaddata /app/fixtures/configuration.json > /dev/null 2>&1 || true
    docker compose exec -T openzaak-web python /app/src/manage.py loaddata /app/fixtures/catalogi.json > /dev/null 2>&1 || true
    echo "  ✓ Loaded OpenZaak catalogi (document type definitions)"

    echo ""
    echo "=== Local Development Ready ==="
    echo ""
    echo "Access URLs:"
    echo "  📱 Main App:        http://localhost:62230"
    echo "  📚 Publicatiebank:  http://localhost:8002/admin  (admin/admin)"
    echo "  📁 OpenZaak:        http://localhost:8001/admin  (admin/admin)"
    echo "  🤖 woo-hoo API:     http://localhost:8003/docs"
    echo ""
    echo "Commands:"
    echo "  just logs          # View all logs"
    echo "  just logs gpp-app  # View specific service logs"
    echo "  just health        # Check service health"
    echo "  just down          # Stop everything"
    echo ""

# =============================================================================
# QUICK START (alias for local)
# =============================================================================

# First-time setup: create .env, build, and start (alias for 'local')
quickstart:
    @just local
