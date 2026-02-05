# GPP Monorepo

A unified monorepo for local development of the Generic Publication Platform (GPP) services.

## Overview

This monorepo consolidates all GPP microservices for easier local development and testing:

| Service | Description | Tech Stack | Port |
|---------|-------------|------------|------|
| **gpp-app** (ODPC) | Publication Composer - UI for creating publications | .NET 8 + Vue 3 | 62230 |
| **publicatiebank** (ODRC) | Publication Registry - stores publications | Django + Celery | 8002 |
| **woo-hoo** | LLM Metadata Extraction - AI-powered document analysis | FastAPI + Python | 8003 |
| **openzaak** | Document Management System | Django | 8001 |
| **nginx** | Unified reverse proxy | nginx | 8080 |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- [just](https://github.com/casey/just) command runner (`brew install just`)
- Node.js 20+ (for frontend development)
- .NET 8 SDK (for backend development, optional)
- [uv](https://github.com/astral-sh/uv) (for Python/woo-hoo development)

### First Time Setup

```bash
# 1. Create environment file
cp .env.example .env

# 2. Add your OpenRouter API key to .env (required for woo-hoo)
#    Get one at: https://openrouter.ai

# 3. Build and start everything
just quickstart

# Or step by step:
just build
just up
```

### Daily Development

```bash
# Start all services
just up

# Start only dependencies (DB, Redis, OpenZaak, Publicatiebank)
just up-deps

# Check health of all services
just health

# View logs
just logs

# Stop everything
just down
```

## Architecture
```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           METADATA GENERATION FLOW                            │
└──────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐    ┌─────────────┐    ┌───────────────┐    ┌──────────────┐
│   Browser   │───▶│   gpp-app   │───▶│ publicatiebank│───▶│   OpenZaak   │
│  (Vue.js)   │    │  (.NET 8)   │    │   (Django)    │    │  (DRC API)   │
└─────────────┘    └─────────────┘    └───────────────┘    └──────────────┘
      │                   │                   │                    │
      │                   │                   │                    │
      │                   ▼                   │                    │
      │            ┌─────────────┐            │                    │
      │            │   woo-hoo   │            │                    │
      │            │  (FastAPI)  │            │                    │
      │            │  LLM/OCR    │            │                    │
      │            └─────────────┘            │                    │
      │                                       │                    │
      │                                       ▼                    │
      │                              ┌───────────────┐             │
      │                              │ celery worker │─────────────┘
      │                              │  (strip_pdf)  │
      │                              └───────────────┘

STEP BY STEP:
═══════════════════════════════════════════════════════════════════════════════

1. DOCUMENT UPLOAD (User → gpp-app → publicatiebank → OpenZaak)
   Browser POST /api/v2/documenten ──▶ gpp-app ──▶ publicatiebank ──▶ OpenZaak
   
2. STRIP_PDF TASK (celery → OpenZaak)  
   celery downloads from OpenZaak ──▶ strips metadata ──▶ uploads NEW to OpenZaak
   
3. METADATA GENERATION (gpp-app → publicatiebank → OpenZaak → woo-hoo)
   gpp-app GET /api/v2/documenten/{uuid}/download ──▶ publicatiebank 
   publicatiebank proxies to OpenZaak ──▶ returns PDF
   gpp-app POST /api/v1/metadata/generate-from-file ──▶ woo-hoo
```
```
                                    ┌──────────────────┐
                                    │   Browser/User   │
                                    └────────┬─────────┘
                                             │
                                             ▼
                                    ┌──────────────────┐
                                    │  nginx (8080)    │
                                    │  Reverse Proxy   │
                                    └────────┬─────────┘
                                             │
              ┌──────────────────────────────┼──────────────────────────────┐
              │                              │                              │
              ▼                              ▼                              ▼
    ┌──────────────────┐          ┌──────────────────┐          ┌──────────────────┐
    │  gpp-app (ODPC)  │          │  publicatiebank  │          │    woo-hoo       │
    │  .NET + Vue      │◄────────►│  (ODRC) Django   │          │    FastAPI       │
    │  Port 62230      │          │  Port 8002       │          │    Port 8003     │
    └────────┬─────────┘          └────────┬─────────┘          └──────────────────┘
             │                             │                              │
             │                             │                              │
             │                             ▼                              │
             │                    ┌──────────────────┐                    │
             │                    │    OpenZaak      │                    │
             │                    │    Port 8001     │                    │
             │                    └────────┬─────────┘                    │
             │                             │                              │
             └─────────────────────────────┼──────────────────────────────┘
                                           │
                              ┌────────────┴────────────┐
                              ▼                         ▼
                    ┌──────────────────┐      ┌──────────────────┐
                    │   PostgreSQL     │      │      Redis       │
                    │   Port 5432      │      │    Port 6379     │
                    └──────────────────┘      └──────────────────┘
```

## Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Main Application | http://localhost:8080 | Auto-login (dev mode) |
| GPP-App Direct | http://localhost:62230 | Auto-login (dev mode) |
| Publicatiebank Admin | http://localhost:8002/admin | admin / admin |
| OpenZaak Admin | http://localhost:8001/admin | admin / admin |
| woo-hoo API Docs | http://localhost:8003/docs | - |
| woo-hoo Health | http://localhost:8003/health | - |

## Development Modes

### Full Docker Stack (Recommended for Testing)

```bash
just up
```

All services run in Docker containers. Best for integration testing and simulating production.

### Hybrid Development (Frontend Focus)

```bash
# Start dependencies in Docker
just up-deps

# Run Vue dev server with hot reload (in a new terminal)
just dev-frontend
```

Access the Vue app at http://localhost:5173 - it proxies API calls to the Docker backend.

### Hybrid Development (woo-hoo Focus)

```bash
# Start dependencies
just up-deps

# Run woo-hoo locally with hot reload
just dev-woo-hoo
```

### Full Local Development

```bash
# Start only infrastructure
just up-infra

# Run each service locally (in separate terminals):
just dev-backend    # .NET backend
just dev-frontend   # Vue frontend
just dev-woo-hoo    # woo-hoo
```

## OIDC / Authentication

In production, GPP uses OIDC (OpenID Connect) for authentication, which provides:
- User identity and roles from the identity provider
- User groups (OrganisationUnits) for authorization

**For local development**, OIDC is bypassed:
- The `OIDC_AUTHORITY` environment variable is intentionally NOT set
- GPP-app automatically logs in as a local developer with admin rights
- Test user groups are seeded via fixtures

If you need to test OIDC integration, you can configure it in `.env`:

```env
OIDC_AUTHORITY=https://your-idp.example.com
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
```

## woo-hoo (LLM Metadata Extraction)

woo-hoo uses LLMs to extract metadata from Dutch government documents. It requires an OpenRouter API key.

### Setup

1. Get an API key from [OpenRouter](https://openrouter.ai)
2. Add it to your `.env`:
   ```env
   OPENROUTER_API_KEY=sk-or-v1-...
   ```

### Supported Models

By default, woo-hoo uses EU-based Mistral models for data sovereignty:
- `mistralai/mistral-large-2512` (default)
- `mistralai/mistral-medium-3.1`
- `mistralai/mistral-small-3.2-24b-instruct-2506`

Change the model in `.env`:
```env
WOO_HOO_MODEL=mistralai/mistral-large-2512
```

### Testing woo-hoo

```bash
# Check health
curl http://localhost:8003/health

# View API docs
open http://localhost:8003/docs

# List available models
curl http://localhost:8003/api/v1/metadata/models

# Generate metadata from a file
curl -X POST http://localhost:8003/api/v1/metadata/generate-from-file \
  -F "file=@document.pdf"
```

## Justfile Commands

Run `just` or `just --list` to see all available commands:

```bash
# Main commands
just up              # Start all services
just down            # Stop all services
just restart         # Restart all services
just logs            # View logs

# Selective startup
just up-infra        # Start only postgres & redis
just up-deps         # Start dependencies (+ openzaak, publicatiebank)
just up-woo-hoo      # Start woo-hoo only

# Development
just dev-frontend    # Vue dev server (hot reload)
just dev-backend     # .NET backend (local)
just dev-woo-hoo     # woo-hoo (hot reload)

# Testing
just test            # Run all tests
just test-gpp-app    # Run gpp-app tests
just test-woo-hoo    # Run woo-hoo tests

# Code quality
just lint            # Lint all code
just format          # Format all code

# Database
just db-shell        # Open psql
just db-odpc         # Connect to ODPC database
just db-publicatiebank # Connect to publicatiebank database

# Utilities
just health          # Check service health
just ps              # Show running containers
just clean           # Clean up Docker resources
```

## Project Structure

```
gppmono/
├── services/
│   ├── gpp-app/           # Publication Composer (.NET + Vue)
│   │   ├── ODPC.Server/   # .NET backend
│   │   ├── ODPC.Test/     # Backend tests
│   │   └── odpc.client/   # Vue frontend
│   ├── publicatiebank/    # Publication Registry (Django)
│   │   └── src/woo_publications/
│   └── woo-hoo/           # LLM Metadata Service (FastAPI)
│       └── src/woo_hoo/
├── docker/
│   ├── nginx/             # Reverse proxy config
│   ├── postgres/init/     # Database initialization
│   └── fixtures/          # Seed data for local dev
├── docker-compose.yml     # Main compose file
├── docker-compose.override.yml  # Local dev overrides
├── justfile               # Command runner recipes
├── .env.example           # Environment template
├── CLAUDE.md              # AI assistant instructions
└── README.md              # This file
```

## Troubleshooting

### Services won't start

```bash
# Check what's running
just ps

# View logs for specific service
just logs gpp-app
just logs publicatiebank

# Rebuild images
just build

# Nuclear option: clean slate
just down-v
just up
```

### Database issues

```bash
# Reset databases (destroys all data!)
just down-v
just up

# Check database health
just db-shell
\l  # List databases
\c ODPC  # Connect to ODPC
\dt  # List tables
```

### woo-hoo not generating metadata

1. Check if `OPENROUTER_API_KEY` is set in `.env`
2. Check woo-hoo logs: `just logs woo-hoo`
3. Test health: `curl http://localhost:8003/health`

### Port conflicts

If ports are already in use, check for running containers:
```bash
docker ps -a
# Kill conflicting containers or change ports in docker-compose.override.yml
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests: `just test`
4. Run linting: `just lint`
5. Submit a pull request

## License

See individual service directories for license information.
