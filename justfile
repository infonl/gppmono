# GPP Monorepo - Development Commands
# Run 'just' or 'just help' to see available commands
#
# Service-specific commands are available via:
#   just woo-hoo <command>   # e.g., just woo-hoo test
#   just gpp-app <command>   # e.g., just gpp-app lint
#
# Or run directly in service directories:
#   cd services/woo-hoo && just test

# Import service-specific justfiles (allows 'just woo-hoo test', etc.)
mod woo-hoo 'services/woo-hoo/justfile'
mod gpp-app 'services/gpp-app/justfile'

# Default recipe: show help
default:
    @just --list --unsorted

# =============================================================================
# MAIN COMMANDS
# =============================================================================

# Start infrastructure services only (postgres, redis, openzaak, publicatiebank)
up *ARGS:
    docker compose up {{ARGS}}

# Start infrastructure in background
up-d:
    docker compose up -d

# Stop all services (all profiles)
down:
    docker compose --profile legacy --profile fastapi down

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

# Start gpp-app only (requires deps to be running) [LEGACY]
up-gpp-app:
    docker compose --profile legacy up -d gpp-app

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

# Run all tests (delegates to service-specific justfiles)
test:
    @echo "=== Running all tests ==="
    @echo ""
    @echo ">>> gpp-app tests"
    just gpp-app::test
    @echo ""
    @echo ">>> woo-hoo tests"
    just woo-hoo::test

# Run gpp-app tests
test-gpp-app:
    just gpp-app::test

# Run gpp-app frontend tests
test-gpp-app-frontend:
    just gpp-app::test-frontend

# Run woo-hoo tests
test-woo-hoo:
    just woo-hoo::test

# Run woo-hoo tests with coverage
test-woo-hoo-cov:
    just woo-hoo::test-cov

# =============================================================================
# BUILD & LINT
# =============================================================================

# Build all Docker images (both legacy and fastapi)
build:
    docker compose --profile legacy --profile fastapi build

# Build specific service [LEGACY]
build-gpp-app:
    docker compose --profile legacy build gpp-app

build-woo-hoo:
    docker compose build woo-hoo

# Lint all code (delegates to service-specific justfiles)
lint:
    @echo "=== Linting all code ==="
    @echo ""
    @echo ">>> gpp-app lint"
    just gpp-app::lint
    @echo ""
    @echo ">>> woo-hoo lint"
    just woo-hoo::lint

# Lint gpp-app
lint-gpp-app:
    just gpp-app::lint

# Lint woo-hoo
lint-woo-hoo:
    just woo-hoo::lint

# Format all code (delegates to service-specific justfiles)
format:
    @echo "=== Formatting all code ==="
    @echo ""
    @echo ">>> gpp-app format"
    just gpp-app::format
    @echo ""
    @echo ">>> woo-hoo format"
    just woo-hoo::format

# Format gpp-app
format-gpp-app:
    just gpp-app::format

# Format woo-hoo
format-woo-hoo:
    just woo-hoo::format

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

# Start entire stack for local development with LEGACY .NET backend
local *ARGS:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "=== GPP Local Development (Legacy .NET Architecture) ==="
    echo ""
    echo "Note: For the new FastAPI architecture, use 'just local-fastapi'"
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
        docker compose --profile legacy build
        echo ""
    fi

    # Start everything with legacy profile
    echo "Starting all services..."
    docker compose --profile legacy up -d {{ARGS}}

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
# QUICK START
# =============================================================================

# Quick start with NEW FastAPI architecture (recommended)
quickstart:
    @just local-fastapi

# Quick start with legacy .NET architecture
quickstart-legacy:
    @just local

# =============================================================================
# NEW FASTAPI ARCHITECTURE
# =============================================================================

# Start new FastAPI architecture (gpp-api + gpp-app-fastapi + frontend via Caddy)
up-fastapi *ARGS:
    docker compose --profile fastapi up {{ARGS}}

# Start FastAPI architecture in detached mode
up-fastapi-d:
    docker compose --profile fastapi up -d

# Start FastAPI dev mode (Vue hot reload on port 5173)
up-fastapi-dev:
    docker compose --profile fastapi-dev up -d gpp-api gpp-app-fastapi gpp-frontend-dev

# Start FastAPI combined mode (single container with embedded frontend)
up-fastapi-combined:
    docker compose --profile fastapi-combined up -d

# Full local dev with new FastAPI architecture
local-fastapi *ARGS:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "=== GPP Local Development (FastAPI Architecture) ==="
    echo ""

    # Ensure .env exists
    if [ ! -f .env ]; then
        echo "Creating .env from .env.example..."
        cp .env.example .env
        echo "⚠️  Created .env - you may need to add OPENROUTER_API_KEY"
        echo ""
    fi

    # Build if images don't exist
    if ! docker images | grep -q "gppmono-gpp-api" 2>/dev/null; then
        echo "Building Docker images (first run, this takes a while)..."
        docker compose --profile fastapi build
        echo ""
    fi

    # Start infrastructure first
    echo "Starting infrastructure..."
    docker compose up -d postgres redis

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

    # Start FastAPI services
    echo ""
    echo "Starting FastAPI services..."
    docker compose --profile fastapi up -d {{ARGS}}

    # Wait for gpp-api
    echo -n "  gpp-api: "
    for i in {1..60}; do
        if curl -sf http://localhost:8004/health > /dev/null 2>&1; then
            echo "✓"
            break
        fi
        sleep 2
        if [ $i -eq 60 ]; then echo "✗ (timeout)"; fi
    done

    # Wait for gpp-app-fastapi
    echo -n "  gpp-app-fastapi: "
    for i in {1..60}; do
        if curl -sf http://localhost:8005/health > /dev/null 2>&1; then
            echo "✓"
            break
        fi
        sleep 2
        if [ $i -eq 60 ]; then echo "✗ (timeout)"; fi
    done

    # Wait for frontend
    echo -n "  gpp-frontend: "
    for i in {1..30}; do
        if curl -sf http://localhost:3000/ > /dev/null 2>&1; then
            echo "✓"
            break
        fi
        sleep 1
        if [ $i -eq 30 ]; then echo "✗ (timeout)"; fi
    done

    # Wait for caddy
    echo -n "  Caddy: "
    for i in {1..30}; do
        if curl -sf http://localhost:8080/caddy-health > /dev/null 2>&1; then
            echo "✓"
            break
        fi
        sleep 1
        if [ $i -eq 30 ]; then echo "✗ (timeout)"; fi
    done

    # Ensure databases exist (in case postgres volume was created before init script)
    echo ""
    echo "Ensuring databases exist..."
    docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE gpp_api;" 2>/dev/null || true
    docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE gpp_app_fastapi;" 2>/dev/null || true

    # Load fixtures for gpp_app_fastapi (creates tables and seeds data)
    echo "Loading fixtures..."
    docker compose exec -T postgres psql -U postgres -d gpp_app_fastapi -f /dev/stdin < ./services/gpp-app-fastapi/fixtures/001_seed_data.sql 2>/dev/null || true
    echo "  ✓ gpp_app_fastapi fixtures loaded"

    # Enable test organisation in publicatiebank
    docker compose exec -T postgres psql -U postgres -d woo_publications -c "
        UPDATE metadata_organisation SET is_actief = true WHERE uuid = '5e1e724c-c3ea-4d0a-aa79-d0b66aefe27c';
    " > /dev/null 2>&1 || true
    echo "  ✓ Test organisation enabled"

    # Load OpenZaak fixtures
    docker compose exec -T openzaak python /app/src/manage.py loaddata /app/fixtures/configuration.json > /dev/null 2>&1 || true
    docker compose exec -T openzaak python /app/src/manage.py loaddata /app/fixtures/catalogi.json > /dev/null 2>&1 || true
    echo "  ✓ OpenZaak fixtures loaded"

    echo ""
    echo "=== FastAPI Local Development Ready ==="
    echo ""
    echo "Access URLs:"
    echo "  📱 Main App (Caddy):     http://localhost:8080"
    echo "  🔧 gpp-api direct:       http://localhost:8004/docs"
    echo "  🔧 gpp-app-fastapi:      http://localhost:8005/docs"
    echo "  🎨 Frontend direct:      http://localhost:3000"
    echo ""
    echo "Commands:"
    echo "  just logs gpp-api           # View gpp-api logs"
    echo "  just logs gpp-app-fastapi   # View gpp-app logs"
    echo "  just logs caddy             # View caddy logs"
    echo "  just health-fastapi         # Check service health"
    echo "  just down                   # Stop everything"
    echo ""

# Health check for FastAPI services
health-fastapi:
    @echo "=== FastAPI Services Health Check ==="
    @echo ""
    @echo "1. PostgreSQL:"
    @docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1 && echo "   ✓ Healthy" || echo "   ✗ Not ready"
    @echo ""
    @echo "2. Redis:"
    @docker compose exec -T redis redis-cli ping > /dev/null 2>&1 && echo "   ✓ Healthy" || echo "   ✗ Not ready"
    @echo ""
    @echo "3. gpp-api (port 8004):"
    @curl -sf http://localhost:8004/health > /dev/null 2>&1 && echo "   ✓ Healthy" || echo "   ✗ Not responding"
    @echo ""
    @echo "4. gpp-app-fastapi (port 8005):"
    @curl -sf http://localhost:8005/health > /dev/null 2>&1 && echo "   ✓ Healthy" || echo "   ✗ Not responding"
    @echo ""
    @echo "5. gpp-frontend (port 3000):"
    @curl -sf http://localhost:3000/ > /dev/null 2>&1 && echo "   ✓ Healthy" || echo "   ✗ Not responding"
    @echo ""
    @echo "6. Caddy (port 8080):"
    @curl -sf http://localhost:8080/caddy-health > /dev/null 2>&1 && echo "   ✓ Healthy" || echo "   ✗ Not responding"
    @echo ""
    @echo "=== Access URLs ==="
    @echo "Main app (via Caddy):  http://localhost:8080"
    @echo "gpp-api docs:          http://localhost:8004/docs"
    @echo "gpp-app-fastapi docs:  http://localhost:8005/docs"
    @echo "Frontend direct:       http://localhost:3000"
    @echo ""

# Build FastAPI services
build-fastapi:
    docker compose --profile fastapi build

# Load/reload fixtures for FastAPI local dev
fixtures-fastapi:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "Loading FastAPI fixtures..."

    # Ensure databases exist
    docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE gpp_api;" 2>/dev/null || true
    docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE gpp_app_fastapi;" 2>/dev/null || true

    # Load gpp_app_fastapi fixtures
    docker compose exec -T postgres psql -U postgres -d gpp_app_fastapi -f /dev/stdin < ./services/gpp-app-fastapi/fixtures/001_seed_data.sql
    echo "  ✓ gpp_app_fastapi fixtures loaded"

    # Enable test organisation
    docker compose exec -T postgres psql -U postgres -d woo_publications -c "
        UPDATE metadata_organisation SET is_actief = true WHERE uuid = '5e1e724c-c3ea-4d0a-aa79-d0b66aefe27c';
    " > /dev/null 2>&1 || true
    echo "  ✓ Test organisation enabled"

    # Load OpenZaak fixtures
    docker compose exec -T openzaak python /app/src/manage.py loaddata /app/fixtures/configuration.json > /dev/null 2>&1 || true
    docker compose exec -T openzaak python /app/src/manage.py loaddata /app/fixtures/catalogi.json > /dev/null 2>&1 || true
    echo "  ✓ OpenZaak fixtures loaded"

    echo ""
    echo "Fixtures loaded successfully!"

# Reset FastAPI databases (drop and recreate)
reset-fastapi-db:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "⚠️  This will DROP and recreate gpp_api and gpp_app_fastapi databases!"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS gpp_api;"
        docker compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS gpp_app_fastapi;"
        docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE gpp_api;"
        docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE gpp_app_fastapi;"
        echo "Databases recreated. Run 'just fixtures-fastapi' to load seed data."
    fi

# View logs for FastAPI services
logs-fastapi *ARGS:
    docker compose --profile fastapi logs -f {{ARGS}}
