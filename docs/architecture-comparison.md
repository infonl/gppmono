# GPP Architecture: Legacy vs New Stack Comparison

This document compares the legacy GPP stack (Django + C#/.NET) with the new FastAPI-based architecture, explaining the benefits and rationale for the migration.

## Architecture Overview

### Legacy Stack
```
Browser
    ↓
Nginx (reverse proxy)
    ├→ gpp-app (C#/.NET 8) - BFF, OIDC, user groups
    ├→ publicatiebank (Django 5.2) - publications, documents, OpenZaak integration
    ├→ publicatiebank-celery (worker) - async tasks
    └→ woo-hoo (FastAPI) - LLM metadata generation
       ↓
    ├→ OpenZaak (Django) - document storage
    ├→ openzaak-celery (worker)
    ├→ PostgreSQL (5 schemas)
    └→ Redis (4 slots: cache + 3 Celery brokers)
```

### New Stack
```
Browser
    ↓
Caddy (reverse proxy)
    ├→ gpp-app-fastapi - BFF, OIDC, user groups
    ├→ gpp-api - publications, documents, OpenZaak integration
    ├→ gpp-api-worker - async tasks (Redis Streams)
    └→ woo-hoo (FastAPI) - LLM metadata generation
       ↓
    ├→ OpenZaak
    ├→ PostgreSQL (3 schemas)
    └→ Redis (1 stream)
```

---

## Key Improvements

### 1. Unified Technology Stack

| Aspect | Legacy | New |
|--------|--------|-----|
| Languages | C#, Python, JavaScript | Python only (+ JS frontend) |
| Frameworks | ASP.NET Core, Django, FastAPI | FastAPI only |
| ORMs | Entity Framework, Django ORM | SQLAlchemy 2.0 async |
| Task Queues | Celery (2 workers) | Redis Streams (1 worker) |

**Benefits:**
- Single language expertise required for backend development
- Consistent patterns across all services
- Easier debugging and profiling
- Shared utilities and libraries between services

### 2. Simplified Async Task Processing

**Legacy: Celery**
```python
# 10+ task definitions with complex state management
@shared_task
def process_source_document(document_id):
    # Download from source
    # Strip metadata (patched behavior)
    # Upload to OpenZaak
    # Update status flags
    # Trigger indexing
    pass
```

Problems:
- Celery broker requires separate Redis database per worker
- Complex task chaining and error handling
- State scattered across Celery result backend and database
- Two separate Celery workers (publicatiebank + openzaak)

**New: Redis Streams**
```python
# Lightweight task handling with consumer groups
async def handle_task(task_type: str, payload: dict):
    match task_type:
        case "index_document":
            await index_document(payload)
        case "sync_to_openzaak":
            await sync_to_openzaak(payload)
```

Benefits:
- Native Redis feature - no additional dependencies
- Built-in consumer groups with message acknowledgment
- Automatic pending message recovery
- Single worker process handles all task types
- Simpler deployment and monitoring

### 3. Elimination of Runtime Patches

**Legacy Problem:**
The `001_fix_informatieobjecttype_url.py` patch monkey-patches Django models at container startup to fix URL construction for OpenZaak integration.

```python
# Legacy: Fragile runtime patching
def apply_patch():
    # Find and modify Document.register_in_documents_api method
    # Insert code to use ZTC service URL
    # Hope it doesn't break on library updates
```

**New Approach:**
Correct URL construction is built into the `gpp-api` OpenZaak client from the start.

```python
# New: Clean integration
class OpenZaakClient:
    def get_informatieobjecttype_url(self, category_uuid: UUID) -> str:
        # Use configured catalogi API URL directly
        return f"{self.settings.openzaak_catalogi_api_url}/informatieobjecttypen/{category_uuid}"
```

Benefits:
- No fragile startup patching
- Testable URL construction logic
- Clear configuration via environment variables
- No risk of patch failing on library updates

### 4. Modern Async Database Access

**Legacy: Django ORM (sync) + Entity Framework**
```python
# Django - synchronous by default
def get_publication(uuid):
    return Publication.objects.get(uuid=uuid)  # Blocking
```

```csharp
// Entity Framework - separate database
var pub = await _context.Publicaties.FindAsync(uuid);
```

**New: SQLAlchemy 2.0 Async**
```python
async def get_publication(db: AsyncSession, uuid: UUID) -> Publication | None:
    result = await db.execute(
        select(Publication)
        .options(selectinload(Publication.documenten))
        .where(Publication.uuid == uuid)
    )
    return result.scalar_one_or_none()
```

Benefits:
- Non-blocking database operations
- Efficient connection pooling with asyncpg
- Eager loading with `selectinload()` prevents N+1 queries
- Type-safe queries with `Mapped[]` annotations
- Single ORM pattern across all services

### 5. Simplified OIDC Authentication

**Legacy: Complex conditional setup**
```csharp
// C# - Duende library with complex configuration
if (!string.IsNullOrEmpty(oidcAuthority))
{
    services.AddOpenIdConnect("oidc", options => {
        // 50+ lines of configuration
    });
}
else
{
    // Dev mode: Auto-login as admin
    services.AddAuthentication(options => {
        // Different auth scheme for dev
    });
}
```

**New: Clean FastAPI approach**
```python
# Authlib with simple configuration
oauth = OAuth()
oauth.register("oidc",
    client_id=settings.oidc_client_id,
    client_secret=settings.oidc_client_secret,
    server_metadata_url=f"{settings.oidc_authority}/.well-known/openid-configuration",
)

# Dev mode check is a simple flag
async def get_current_user(request: Request) -> OdpcUser:
    if settings.dev_mode:
        return OdpcUser(id="dev", is_admin=True, ...)
    return await get_oidc_user(request)
```

Benefits:
- Simpler configuration with Pydantic settings
- Consistent auth dependency injection
- Clear separation of dev/prod modes
- Fewer dependencies (Authlib vs Duende stack)

### 6. Caddy vs Nginx

**Legacy: Nginx**
```nginx
# Manual configuration with multiple location blocks
location /api/v1/metadata/ {
    proxy_pass http://gpp-app:62230;
    proxy_read_timeout 120s;  # For LLM calls
}
location /api/v2/ {
    proxy_pass http://publicatiebank:8002;
}
# ... 15+ more location blocks
```

**New: Caddy**
```caddyfile
:80 {
    handle /api/me { reverse_proxy gpp-app:8000 }
    handle /api/v1/* { reverse_proxy gpp-app:8000 }
    handle /api/v2/* { reverse_proxy gpp-api:8000 }
    handle /admin/* { reverse_proxy gpp-api:8000 }
    handle { reverse_proxy gpp-api:8000 }
}
```

Benefits:
- Automatic HTTPS with Let's Encrypt (production)
- Simpler configuration syntax
- Built-in health checks
- Modern HTTP/2 and HTTP/3 support
- Automatic config reloading

### 7. Reduced Database Complexity

**Legacy: 5 PostgreSQL schemas + 4 Redis slots**
- `postgres` - default
- `openzaak` - OpenZaak data
- `woo_publications` - publicatiebank
- `odpc` - gpp-app C# service
- `gpp_zoeken` - search index

Redis:
- Slot 0: Cache
- Slot 1: publicatiebank Celery
- Slot 2: openzaak Celery
- Slot 3: Available

**New: 3 PostgreSQL schemas + 1 Redis stream**
- `openzaak` - OpenZaak (unchanged)
- `gpp_api` - publications, documents, metadata
- `gpp_app` - user groups only

Redis:
- Single stream: `gpp_tasks`

Benefits:
- Fewer database connections to manage
- Simpler backup/restore procedures
- Less Redis memory usage
- Easier local development setup

### 8. Better Testing Infrastructure

**Legacy:**
- C# xUnit tests (separate project)
- Django pytest (different patterns)
- No integration tests between services
- Mocking across language boundaries is complex

**New:**
- Unified pytest across all services
- Consistent fixtures and patterns
- respx for HTTP mocking
- In-memory SQLite for fast unit tests
- Easy to add integration tests

```python
# Consistent test pattern across services
@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

async def test_list_publications(client, test_session, test_eigenaar):
    # Same pattern works in gpp-api and gpp-app-fastapi
    response = await client.get("/api/v2/publicaties")
    assert response.status_code == 200
```

### 9. Type Safety Throughout

**Legacy: Mixed type systems**
- C# has strong types but isolated from Python
- Django has optional type hints
- No shared type definitions

**New: Consistent Pydantic models**
```python
# Shared schema patterns
class PublicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    officiele_titel: str = Field(alias="officieleTitel")
    publicatiestatus: str
    documenten: list[DocumentResponse] = []
```

Benefits:
- Runtime validation
- Automatic OpenAPI schema generation
- IDE autocomplete across the stack
- Consistent serialization (camelCase for API, snake_case internal)

### 10. Simplified Deployment

**Legacy Docker Compose:**
```yaml
services:
  gpp-app:           # C# with complex build
  publicatiebank:    # Django with Node.js multi-stage
  publicatiebank-celery:  # Same image, different entrypoint
  openzaak:          # External image
  openzaak-celery:   # Same image, worker mode
  nginx:             # Reverse proxy
  postgres:          # Database
  redis:             # Cache + brokers
  # Total: 8 containers minimum
```

**New Docker Compose:**
```yaml
services:
  gpp-api:           # FastAPI
  gpp-api-worker:    # Same image, worker mode
  gpp-app-fastapi:   # FastAPI
  openzaak:          # External image (unchanged)
  caddy:             # Reverse proxy
  postgres:          # Database
  redis:             # Single purpose
  # Total: 7 containers, simpler builds
```

---

## Migration Path

The new services are designed for gradual migration:

1. **Phase 1**: Deploy gpp-api alongside publicatiebank (both serve /api/v2/)
2. **Phase 2**: Switch Caddy to route to gpp-api, keep publicatiebank as fallback
3. **Phase 3**: Deploy gpp-app-fastapi, migrate user groups
4. **Phase 4**: Remove legacy services

Each phase can be tested independently with feature flags.

---

## Performance Expectations

| Metric | Legacy | New | Improvement |
|--------|--------|-----|-------------|
| Cold start | ~5s (Django) | ~1s (FastAPI) | 5x faster |
| Memory per worker | ~200MB | ~80MB | 2.5x less |
| Request latency | ~50ms | ~20ms | 2.5x faster |
| Database connections | 10+ pools | 3 pools | 70% fewer |
| Container count | 8+ | 7 | Simpler ops |

*Estimates based on similar FastAPI vs Django migrations*

---

## Conclusion

The new FastAPI-based architecture addresses the key pain points of the legacy stack:

1. **Complexity**: Single language, single framework, consistent patterns
2. **Fragility**: No runtime patches, clean integrations
3. **Performance**: Async throughout, efficient resource usage
4. **Maintainability**: Unified testing, type safety, simpler deployment
5. **Developer Experience**: One stack to learn, better tooling

The migration is designed to be incremental, allowing the team to validate each component before full cutover.
