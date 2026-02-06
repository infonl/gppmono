# GPP Backend Rewrite: Django + C# → FastAPI

## Overview

Replace the existing Django (publicatiebank) and C#/.NET (gpp-app) backends with two FastAPI microservices.

 alway smake sure ebverything has good etst coverage for python use pytest and functional style not unittest with testcase classes. use pytest fixtures and pytest async where elegant. make sure everything has good etst coverage and is formattetd with ruff and uses uv and all is wrapped in just files and docker compose files.
### Target Architecture

```
┌────────────────────────────────────────────────────────────┐
│                         Caddy                              │
└───────────────────────────┬────────────────────────────────┘
                            │
       ┌────────────────────┼────────────────────┐
       ▼                    ▼                    ▼
  ┌─────────┐         ┌──────────┐         ┌──────────┐
  │ gpp-api │◄────────│ gpp-app  │────────►│ woo-hoo  │
  │ FastAPI │         │ FastAPI  │         │ (keep)   │
  └────┬────┘         └────┬─────┘         └──────────┘
       │                   │
       └─────────┬─────────┘
                 ▼
          ┌────────────┐
          │ PostgreSQL │
          └──────┬─────┘
                 │
                 ▼
          ┌────────────┐
          │   Redis    │
          │ (streams)  │
          └──────┬─────┘
                 │
          ┌──────┴──────┐
          ▼             ▼
    ┌──────────┐  ┌──────────────┐
    │ worker   │  │ OpenZaak /   │
    │ process  │  │ GPP-Zoeken   │
    └──────────┘  └──────────────┘
```

### Service Responsibilities

| Service | Replaces | Framework | Responsibility |
|---------|----------|-----------|----------------|
| **gpp-api** | publicatiebank (Django) | FastAPI | Domain logic, data, OpenZaak integration, search indexing |
| **gpp-app** | ODPC.Server (C#) | FastAPI | BFF, OIDC auth, authorization, user groups, proxies |
| **woo-hoo** | - | FastAPI | LLM metadata generation (keep as-is) |

---

## Phase 1: Project Setup & Infrastructure

### 1.1 Create gpp-api service structure

- [ ] Create `services/gpp-api/` directory
- [ ] Initialize with `uv init`
- [ ] Create `pyproject.toml` with dependencies:
  ```toml
  [project]
  name = "gpp-api"
  version = "0.1.0"
  requires-python = ">=3.12"
  dependencies = [
      "fastapi>=0.115",
      "uvicorn[standard]",
      "sqlalchemy[asyncio]>=2.0",
      "asyncpg",
      "alembic",
      "pydantic-settings>=2.0",
      "httpx",
      "redis>=5.0",
      "transitions",
      "starlette-admin",
      "structlog",
      "python-multipart",
  ]

  [project.optional-dependencies]
  dev = ["pytest", "pytest-asyncio", "pytest-cov", "ruff", "pyright"]
  ```
- [ ] Create directory structure:
  ```
  gpp-api/
  ├── src/gpp_api/
  │   ├── __init__.py
  │   ├── main.py
  │   ├── config.py
  │   ├── db/
  │   │   ├── __init__.py
  │   │   ├── engine.py
  │   │   └── models/
  │   ├── api/
  │   │   ├── __init__.py
  │   │   ├── deps.py
  │   │   └── v2/
  │   ├── services/
  │   ├── workers/
  │   └── admin/
  ├── tests/
  ├── alembic/
  ├── alembic.ini
  ├── Dockerfile
  └── pyproject.toml
  ```

### 1.2 Create gpp-app service structure

- [ ] Create `services/gpp-app-fastapi/` directory (parallel to existing during migration)
- [ ] Initialize with `uv init`
- [ ] Create `pyproject.toml` with dependencies:
  ```toml
  [project]
  name = "gpp-app"
  version = "0.1.0"
  requires-python = ">=3.12"
  dependencies = [
      "fastapi>=0.115",
      "uvicorn[standard]",
      "sqlalchemy[asyncio]>=2.0",
      "asyncpg",
      "alembic",
      "pydantic-settings>=2.0",
      "httpx",
      "redis>=5.0",
      "authlib",
      "itsdangerous",
      "starlette[full]",
      "structlog",
  ]
  ```
- [ ] Create directory structure:
  ```
  gpp-app-fastapi/
  ├── src/gpp_app/
  │   ├── __init__.py
  │   ├── main.py
  │   ├── config.py
  │   ├── db/
  │   ├── api/
  │   ├── auth/
  │   └── services/
  ├── tests/
  ├── alembic/
  ├── Dockerfile
  └── pyproject.toml
  ```

### 1.3 Replace nginx with Caddy

- [ ] Create `docker/caddy/Caddyfile`:
  ```caddyfile
  :80 {
      # Health check
      handle /caddy-health {
          respond "healthy" 200
      }

      # gpp-app (BFF) routes
      handle /api/me {
          reverse_proxy gpp-app:8000
      }
      handle /api/challenge {
          reverse_proxy gpp-app:8000
      }
      handle /api/logoff {
          reverse_proxy gpp-app:8000
      }
      handle /api/v1/gebruikersgroepen* {
          reverse_proxy gpp-app:8000
      }
      handle /api/v1/publicaties* {
          reverse_proxy gpp-app:8000
      }
      handle /api/v1/documenten* {
          reverse_proxy gpp-app:8000
      }
      handle /api/v1/metadata* {
          reverse_proxy gpp-app:8000
      }

      # gpp-api (data) routes
      handle /api/v2/* {
          reverse_proxy gpp-api:8000
      }
      handle /admin/* {
          reverse_proxy gpp-api:8000
      }

      # woo-hoo routes
      handle /woo-hoo/* {
          uri strip_prefix /woo-hoo
          reverse_proxy woo-hoo:8000
      }

      # Default to gpp-api
      handle {
          reverse_proxy gpp-api:8000
      }
  }
  ```
- [ ] Update `docker-compose.yml` to use Caddy instead of nginx
- [ ] Test routing works correctly

---

## Phase 2: gpp-api Core (Database & Models)

### 2.1 Database Engine Setup

- [ ] Create `src/gpp_api/db/engine.py`:
  ```python
  from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
  from sqlalchemy.orm import DeclarativeBase
  from ..config import settings

  engine = create_async_engine(
      settings.database_url,
      echo=settings.debug,
      pool_pre_ping=True,
  )

  async_session = async_sessionmaker(engine, expire_on_commit=False)

  class Base(DeclarativeBase):
      pass

  async def get_db() -> AsyncSession:
      async with async_session() as session:
          yield session
  ```

### 2.2 Core Models (SQLAlchemy 2.0)

- [ ] Create `src/gpp_api/db/models/publication.py`:
  - Publication model with UUID primary key
  - Document model with file metadata
  - State machine integration via `transitions` library
  - Relationships: Publication → Documents (one-to-many)

- [ ] Create `src/gpp_api/db/models/metadata.py`:
  - InformationCategory model (with retention policy fields)
  - Organisation model (publisher/liable/drafter)
  - Theme model (hierarchical with materialized path or adjacency list)
  - Topic model

- [ ] Create `src/gpp_api/db/models/accounts.py`:
  - User model (minimal, for audit trail)
  - OrganisationMember model
  - OrganisationUnit model

- [ ] Create `src/gpp_api/db/models/api.py`:
  - Application model (API tokens)

### 2.3 State Machine Implementation

- [ ] Create `src/gpp_api/services/state_machine.py`:
  ```python
  from transitions import Machine
  from enum import Enum

  class PublicationState(str, Enum):
      CONCEPT = "concept"
      PUBLISHED = "gepubliceerd"
      REVOKED = "ingetrokken"

  class PublicationStateMachine:
      states = [s.value for s in PublicationState]

      def __init__(self, publication):
          self.publication = publication
          self.machine = Machine(
              model=self,
              states=self.states,
              initial=publication.status or PublicationState.CONCEPT.value,
              auto_transitions=False,
          )

          # Define transitions
          self.machine.add_transition(
              trigger='publish',
              source=PublicationState.CONCEPT.value,
              dest=PublicationState.PUBLISHED.value,
              before='_before_publish',
              after='_after_publish',
          )
          self.machine.add_transition(
              trigger='revoke',
              source=PublicationState.PUBLISHED.value,
              dest=PublicationState.REVOKED.value,
              after='_after_revoke',
          )

      async def _before_publish(self):
          # Validate all required fields
          pass

      async def _after_publish(self):
          # Queue indexing task
          pass

      async def _after_revoke(self):
          # Queue removal from index
          pass
  ```

### 2.4 Alembic Migrations

- [ ] Initialize Alembic: `alembic init alembic`
- [ ] Configure `alembic.ini` for async
- [ ] Create initial migration with all models
- [ ] Test migration up/down

---

## Phase 3: gpp-api Background Tasks (Redis Streams)

### 3.1 Redis Client Setup

- [ ] Create `src/gpp_api/services/redis.py`:
  ```python
  import redis.asyncio as redis
  from ..config import settings

  redis_client: redis.Redis | None = None

  async def get_redis() -> redis.Redis:
      global redis_client
      if redis_client is None:
          redis_client = redis.from_url(
              settings.redis_url,
              encoding="utf-8",
              decode_responses=True,
          )
      return redis_client

  async def close_redis():
      global redis_client
      if redis_client:
          await redis_client.close()
          redis_client = None
  ```

### 3.2 Task Queue with Redis Streams

- [ ] Create `src/gpp_api/workers/queue.py`:
  ```python
  import json
  from datetime import datetime
  from ..services.redis import get_redis

  STREAM_NAME = "gpp_tasks"
  CONSUMER_GROUP = "gpp_workers"

  async def enqueue_task(task_type: str, payload: dict) -> str:
      """Add task to Redis Stream."""
      redis = await get_redis()
      message_id = await redis.xadd(
          STREAM_NAME,
          {
              "type": task_type,
              "payload": json.dumps(payload),
              "created_at": datetime.utcnow().isoformat(),
          },
      )
      return message_id

  async def ensure_consumer_group():
      """Create consumer group if it doesn't exist."""
      redis = await get_redis()
      try:
          await redis.xgroup_create(
              STREAM_NAME,
              CONSUMER_GROUP,
              id="0",
              mkstream=True,
          )
      except redis.ResponseError as e:
          if "BUSYGROUP" not in str(e):
              raise
  ```

### 3.3 Worker Process

- [ ] Create `src/gpp_api/workers/worker.py`:
  ```python
  import asyncio
  import json
  import signal
  from typing import Callable, Awaitable
  import structlog
  from ..services.redis import get_redis, close_redis
  from .queue import STREAM_NAME, CONSUMER_GROUP

  logger = structlog.get_logger()

  TaskHandler = Callable[[dict], Awaitable[None]]

  class Worker:
      def __init__(self, consumer_name: str):
          self.consumer_name = consumer_name
          self.handlers: dict[str, TaskHandler] = {}
          self.running = False

      def register(self, task_type: str):
          """Decorator to register task handlers."""
          def decorator(func: TaskHandler):
              self.handlers[task_type] = func
              return func
          return decorator

      async def process_message(self, message_id: str, data: dict):
          """Process a single message."""
          task_type = data.get("type")
          payload = json.loads(data.get("payload", "{}"))

          handler = self.handlers.get(task_type)
          if not handler:
              logger.warning("Unknown task type", task_type=task_type)
              return

          try:
              await handler(payload)
              # Acknowledge successful processing
              redis = await get_redis()
              await redis.xack(STREAM_NAME, CONSUMER_GROUP, message_id)
              logger.info("Task completed", task_type=task_type, message_id=message_id)
          except Exception as e:
              logger.error("Task failed", task_type=task_type, error=str(e))
              # Don't ack - will be reprocessed or moved to dead letter

      async def run(self):
          """Main worker loop."""
          self.running = True
          redis = await get_redis()

          # First, process any pending messages (unacked from previous run)
          pending = await redis.xpending_range(
              STREAM_NAME, CONSUMER_GROUP,
              min="-", max="+", count=100,
              consumername=self.consumer_name,
          )
          for p in pending:
              messages = await redis.xclaim(
                  STREAM_NAME, CONSUMER_GROUP, self.consumer_name,
                  min_idle_time=60000,  # 1 minute
                  message_ids=[p["message_id"]],
              )
              for msg_id, data in messages:
                  await self.process_message(msg_id, data)

          # Then listen for new messages
          while self.running:
              try:
                  messages = await redis.xreadgroup(
                      CONSUMER_GROUP,
                      self.consumer_name,
                      {STREAM_NAME: ">"},
                      count=10,
                      block=5000,
                  )
                  for stream, entries in messages:
                      for message_id, data in entries:
                          await self.process_message(message_id, data)
              except asyncio.CancelledError:
                  break
              except Exception as e:
                  logger.error("Worker error", error=str(e))
                  await asyncio.sleep(1)

      async def stop(self):
          self.running = False
          await close_redis()

  # Global worker instance
  worker = Worker(consumer_name="worker-1")
  ```

### 3.4 Task Definitions

- [ ] Create `src/gpp_api/workers/tasks.py`:
  ```python
  import httpx
  import structlog
  from ..config import settings
  from ..db.engine import async_session
  from ..db.models.publication import Document, Publication
  from .worker import worker
  from .queue import enqueue_task

  logger = structlog.get_logger()

  @worker.register("index_document")
  async def index_document(payload: dict):
      """Index document in GPP-Zoeken."""
      document_uuid = payload["uuid"]

      async with async_session() as session:
          doc = await session.get(Document, document_uuid)
          if not doc:
              logger.warning("Document not found", uuid=document_uuid)
              return

          if doc.status != "gepubliceerd":
              logger.info("Document not published, skipping", uuid=document_uuid)
              return

          async with httpx.AsyncClient() as client:
              response = await client.post(
                  f"{settings.gpp_zoeken_url}/index/document",
                  json={
                      "uuid": str(doc.uuid),
                      "title": doc.title,
                      "publication_uuid": str(doc.publication_uuid),
                      # ... other fields
                  },
                  timeout=30.0,
              )
              response.raise_for_status()

  @worker.register("index_publication")
  async def index_publication(payload: dict):
      """Index publication in GPP-Zoeken."""
      publication_uuid = payload["uuid"]
      # Similar implementation...

  @worker.register("remove_from_index")
  async def remove_from_index(payload: dict):
      """Remove document/publication from search index."""
      uuid = payload["uuid"]
      index_type = payload["type"]  # "document" or "publication"

      async with httpx.AsyncClient() as client:
          response = await client.delete(
              f"{settings.gpp_zoeken_url}/index/{index_type}/{uuid}",
              timeout=10.0,
          )
          if response.status_code != 404:
              response.raise_for_status()

  @worker.register("sync_to_openzaak")
  async def sync_to_openzaak(payload: dict):
      """Sync document to OpenZaak Documents API."""
      document_uuid = payload["uuid"]
      action = payload["action"]  # "create", "update", "delete"
      # Implementation with retry logic...

  # Helper to enqueue tasks
  async def queue_index_document(uuid: str):
      await enqueue_task("index_document", {"uuid": uuid})

  async def queue_index_publication(uuid: str):
      await enqueue_task("index_publication", {"uuid": uuid})

  async def queue_remove_from_index(uuid: str, index_type: str):
      await enqueue_task("remove_from_index", {"uuid": uuid, "type": index_type})
  ```

### 3.5 Worker Entry Point

- [ ] Create `src/gpp_api/workers/__main__.py`:
  ```python
  import asyncio
  import signal
  from .worker import worker
  from .queue import ensure_consumer_group
  from . import tasks  # noqa: F401 - registers handlers

  async def main():
      await ensure_consumer_group()

      loop = asyncio.get_event_loop()
      loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(worker.stop()))
      loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(worker.stop()))

      await worker.run()

  if __name__ == "__main__":
      asyncio.run(main())
  ```
- [ ] Add worker to docker-compose as separate service

---

## Phase 4: gpp-api REST Endpoints

### 4.1 Pydantic Schemas

- [ ] Create `src/gpp_api/api/schemas/publication.py`:
  - PublicationCreate, PublicationUpdate, PublicationResponse
  - DocumentCreate, DocumentUpdate, DocumentResponse
  - Proper validation with Pydantic v2

- [ ] Create `src/gpp_api/api/schemas/metadata.py`:
  - InformationCategoryResponse
  - OrganisationResponse
  - ThemeResponse, TopicResponse

### 4.2 API Endpoints

- [ ] Create `src/gpp_api/api/v2/publications.py`:
  ```python
  from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
  from sqlalchemy.ext.asyncio import AsyncSession
  from ...db.engine import get_db
  from ...db.models.publication import Publication
  from ...workers.tasks import queue_index_publication
  from ..schemas.publication import PublicationCreate, PublicationResponse

  router = APIRouter(prefix="/publicaties", tags=["publications"])

  @router.post("/", response_model=PublicationResponse)
  async def create_publication(
      data: PublicationCreate,
      background_tasks: BackgroundTasks,
      db: AsyncSession = Depends(get_db),
  ):
      publication = Publication(**data.model_dump())
      db.add(publication)
      await db.commit()
      await db.refresh(publication)
      return publication

  @router.get("/{uuid}", response_model=PublicationResponse)
  async def get_publication(uuid: str, db: AsyncSession = Depends(get_db)):
      publication = await db.get(Publication, uuid)
      if not publication:
          raise HTTPException(status_code=404, detail="Publication not found")
      return publication

  @router.put("/{uuid}", response_model=PublicationResponse)
  async def update_publication(
      uuid: str,
      data: PublicationUpdate,
      db: AsyncSession = Depends(get_db),
  ):
      # Implementation with state machine validation
      pass

  @router.post("/{uuid}/publish")
  async def publish_publication(uuid: str, db: AsyncSession = Depends(get_db)):
      """Transition publication to published state."""
      publication = await db.get(Publication, uuid)
      if not publication:
          raise HTTPException(status_code=404)

      # Use state machine
      sm = PublicationStateMachine(publication)
      sm.publish()  # Will raise if transition not allowed

      publication.status = sm.state
      await db.commit()

      # Queue indexing via Redis Stream
      await queue_index_publication(str(uuid))

      return {"status": "published"}
  ```

- [ ] Create `src/gpp_api/api/v2/documents.py`:
  - CRUD endpoints
  - File upload with multipart
  - Download endpoint with streaming

- [ ] Create `src/gpp_api/api/v2/organisations.py`
- [ ] Create `src/gpp_api/api/v2/categories.py`
- [ ] Create `src/gpp_api/api/v2/topics.py`

### 4.3 OpenZaak Client

- [ ] Create `src/gpp_api/services/openzaak.py`:
  ```python
  import httpx
  from ..config import settings

  class OpenZaakClient:
      def __init__(self):
          self.base_url = settings.openzaak_url
          self.api_key = settings.openzaak_api_key

      async def _request(self, method: str, path: str, **kwargs):
          async with httpx.AsyncClient() as client:
              response = await client.request(
                  method,
                  f"{self.base_url}{path}",
                  headers={
                      "Authorization": f"Token {self.api_key}",
                      "Content-Type": "application/json",
                  },
                  **kwargs,
              )
              response.raise_for_status()
              return response.json()

      async def create_document(self, data: dict) -> dict:
          return await self._request("POST", "/documenten/api/v1/enkelvoudiginformatieobjecten", json=data)

      async def upload_file_part(self, document_url: str, part_data: bytes, part_number: int):
          # Multipart upload implementation
          pass

      async def lock_document(self, document_url: str) -> str:
          """Lock document for editing, returns lock ID."""
          response = await self._request("POST", f"{document_url}/lock")
          return response["lock"]

      async def unlock_document(self, document_url: str, lock_id: str):
          await self._request("POST", f"{document_url}/unlock", json={"lock": lock_id})
  ```

### 4.4 Starlette-Admin Setup

- [ ] Create `src/gpp_api/admin/views.py`:
  ```python
  from starlette_admin.contrib.sqla import Admin, ModelView
  from starlette_admin import action
  from ..db.models.publication import Publication, Document
  from ..db.models.metadata import InformationCategory, Organisation, Topic

  class PublicationAdmin(ModelView):
      fields = ["uuid", "title", "status", "created_at", "publisher"]
      fields_default_sort = [("created_at", True)]
      searchable_fields = ["title", "uuid"]
      sortable_fields = ["created_at", "status", "title"]

      @action(
          name="publish",
          text="Publish Selected",
          confirmation="Publish selected publications?",
      )
      async def publish_action(self, request, pks):
          # Bulk publish action
          pass

  class DocumentAdmin(ModelView):
      fields = ["uuid", "title", "status", "publication", "created_at"]
      exclude_fields_from_create = ["uuid", "created_at"]

  class OrganisationAdmin(ModelView):
      fields = ["uuid", "name", "rsin", "is_active"]
      searchable_fields = ["name", "rsin"]

  class InformationCategoryAdmin(ModelView):
      fields = ["uuid", "name", "retention_years", "archive_action"]

  def setup_admin(app, engine):
      admin = Admin(
          engine,
          title="GPP Admin",
          base_url="/admin",
      )
      admin.add_view(PublicationAdmin(Publication))
      admin.add_view(DocumentAdmin(Document))
      admin.add_view(OrganisationAdmin(Organisation))
      admin.add_view(InformationCategoryAdmin(InformationCategory))
      admin.mount_to(app)
  ```

---

## Phase 5: gpp-app (BFF) Implementation

### 5.1 OIDC Authentication with Authlib

- [ ] Create `src/gpp_app/auth/oidc.py`:
  ```python
  from authlib.integrations.starlette_client import OAuth
  from starlette.middleware.sessions import SessionMiddleware
  from fastapi import Request, HTTPException
  from ..config import settings

  oauth = OAuth()

  def setup_oauth(app):
      app.add_middleware(
          SessionMiddleware,
          secret_key=settings.session_secret,
          max_age=3600,  # 1 hour
      )

      if settings.oidc_authority:
          oauth.register(
              name="oidc",
              client_id=settings.oidc_client_id,
              client_secret=settings.oidc_client_secret,
              server_metadata_url=f"{settings.oidc_authority}/.well-known/openid-configuration",
              client_kwargs={"scope": "openid profile email"},
          )

  async def get_current_user(request: Request) -> dict | None:
      user = request.session.get("user")
      if not user and settings.auto_login_enabled:
          # Dev mode: auto-login
          return {
              "id": "local-dev",
              "name": "Local Developer",
              "email": "dev@localhost",
              "roles": [settings.oidc_admin_role],
          }
      return user

  async def require_auth(request: Request) -> dict:
      user = await get_current_user(request)
      if not user:
          raise HTTPException(status_code=401, detail="Not authenticated")
      return user

  async def require_admin(request: Request) -> dict:
      user = await require_auth(request)
      if settings.oidc_admin_role not in user.get("roles", []):
          raise HTTPException(status_code=403, detail="Admin access required")
      return user
  ```

### 5.2 Auth Endpoints

- [ ] Create `src/gpp_app/api/auth.py`:
  ```python
  from fastapi import APIRouter, Request
  from fastapi.responses import RedirectResponse
  from ..auth.oidc import oauth, get_current_user
  from ..config import settings

  router = APIRouter(tags=["auth"])

  @router.get("/api/me")
  async def me(request: Request):
      user = await get_current_user(request)
      if not user:
          return {"authenticated": False}
      return {
          "authenticated": True,
          "id": user.get("id"),
          "name": user.get("name"),
          "email": user.get("email"),
          "isAdmin": settings.oidc_admin_role in user.get("roles", []),
      }

  @router.get("/api/challenge")
  async def challenge(request: Request):
      if not settings.oidc_authority:
          # Dev mode - auto login
          request.session["user"] = {
              "id": "local-dev",
              "name": "Local Developer",
              "roles": [settings.oidc_admin_role],
          }
          return RedirectResponse(url="/")

      redirect_uri = request.url_for("auth_callback")
      return await oauth.oidc.authorize_redirect(request, redirect_uri)

  @router.get("/api/callback")
  async def auth_callback(request: Request):
      token = await oauth.oidc.authorize_access_token(request)
      userinfo = token.get("userinfo", {})

      request.session["user"] = {
          "id": userinfo.get(settings.oidc_id_claim, userinfo.get("email")),
          "name": userinfo.get(settings.oidc_name_claim, "Unknown"),
          "email": userinfo.get("email"),
          "roles": userinfo.get(settings.oidc_role_claim, []),
      }
      return RedirectResponse(url="/")

  @router.get("/api/logoff")
  async def logoff(request: Request):
      request.session.clear()
      return RedirectResponse(url="/")
  ```

### 5.3 User Groups (Local DB)

- [ ] Create `src/gpp_app/db/models/user_groups.py`:
  ```python
  from sqlalchemy import Column, String, Table, ForeignKey
  from sqlalchemy.dialects.postgresql import UUID
  from sqlalchemy.orm import relationship
  import uuid
  from .base import Base

  gebruikersgroep_waardelijsten = Table(
      "gebruikersgroep_waardelijsten",
      Base.metadata,
      Column("groep_id", UUID, ForeignKey("gebruikersgroepen.uuid")),
      Column("waardelijst_item", String),
  )

  gebruikersgroep_gebruikers = Table(
      "gebruikersgroep_gebruikers",
      Base.metadata,
      Column("groep_id", UUID, ForeignKey("gebruikersgroepen.uuid")),
      Column("gebruiker_id", String),
  )

  class Gebruikersgroep(Base):
      __tablename__ = "gebruikersgroepen"

      uuid = Column(UUID, primary_key=True, default=uuid.uuid4)
      naam = Column(String, unique=True, nullable=False)

      waardelijsten = relationship(
          "GebruikersgroepWaardelijst",
          back_populates="groep",
          cascade="all, delete-orphan",
      )
      gebruikers = relationship(
          "GebruikersgroepGebruiker",
          back_populates="groep",
          cascade="all, delete-orphan",
      )
  ```

- [ ] Create `src/gpp_app/api/user_groups.py` with CRUD endpoints

### 5.4 Authorization Service

- [ ] Create `src/gpp_app/auth/permissions.py`:
  ```python
  from fastapi import Depends, HTTPException
  from sqlalchemy.ext.asyncio import AsyncSession
  from ..db.engine import get_db
  from ..db.models.user_groups import Gebruikersgroep

  async def get_user_waardelijsten(
      user_id: str,
      db: AsyncSession = Depends(get_db),
  ) -> set[str]:
      """Get all waardelijst items the user has access to."""
      # Query user's groups and their waardelijsten
      # Return set of allowed waardelijst items
      pass

  async def check_publication_access(
      user_id: str,
      publisher: str,
      categories: list[str],
      topics: list[str],
      db: AsyncSession = Depends(get_db),
  ):
      """Validate user has access to create/edit publication with given values."""
      allowed = await get_user_waardelijsten(user_id, db)

      if publisher not in allowed:
          raise HTTPException(400, f"Not authorized for publisher: {publisher}")

      for cat in categories:
          if cat not in allowed:
              raise HTTPException(400, f"Not authorized for category: {cat}")

      for topic in topics:
          if topic not in allowed:
              raise HTTPException(400, f"Not authorized for topic: {topic}")
  ```

### 5.5 Proxy to gpp-api

- [ ] Create `src/gpp_app/services/gpp_api_client.py`:
  ```python
  import httpx
  from ..config import settings

  class GppApiClient:
      def __init__(self, audit_user_id: str, audit_user_name: str):
          self.base_url = settings.gpp_api_url
          self.audit_headers = {
              "Audit-User-ID": audit_user_id,
              "Audit-User-Representation": audit_user_name,
          }

      async def _request(self, method: str, path: str, **kwargs):
          async with httpx.AsyncClient() as client:
              headers = {**self.audit_headers, **kwargs.pop("headers", {})}
              response = await client.request(
                  method,
                  f"{self.base_url}{path}",
                  headers=headers,
                  **kwargs,
              )
              return response

      async def get_publication(self, uuid: str):
          response = await self._request("GET", f"/api/v2/publicaties/{uuid}")
          response.raise_for_status()
          return response.json()

      async def create_publication(self, data: dict):
          response = await self._request("POST", "/api/v2/publicaties", json=data)
          response.raise_for_status()
          return response.json()

      # ... other methods
  ```

### 5.6 woo-hoo Proxy

- [ ] Create `src/gpp_app/api/metadata.py`:
  ```python
  from fastapi import APIRouter, Depends, HTTPException
  import httpx
  from ..auth.oidc import require_auth
  from ..config import settings

  router = APIRouter(prefix="/api/v1/metadata", tags=["metadata"])

  @router.get("/health")
  async def health():
      """Check woo-hoo service availability."""
      if not settings.woo_hoo_url:
          raise HTTPException(503, "Metadata service not configured")

      async with httpx.AsyncClient() as client:
          try:
              response = await client.get(
                  f"{settings.woo_hoo_url}/health",
                  timeout=settings.woo_hoo_health_timeout,
              )
              if response.is_success:
                  return {"status": "available"}
          except Exception:
              pass

      raise HTTPException(502, "Metadata service unavailable")

  @router.post("/generate/{document_uuid}")
  async def generate_metadata(
      document_uuid: str,
      user: dict = Depends(require_auth),
  ):
      """Generate metadata suggestions for a document."""
      # 1. Download document from gpp-api
      # 2. Send to woo-hoo
      # 3. Return suggestions
      pass
  ```

---

## Phase 6: Data Migration

### 6.1 Migration Scripts

- [ ] Create `scripts/migrate_data.py`:
  - Export data from Django to JSON
  - Import JSON into new SQLAlchemy models
  - Verify data integrity

### 6.2 Parallel Running

- [ ] Configure both old and new services to run simultaneously
- [ ] Add feature flag to route traffic to new services
- [ ] Create comparison tests to verify API compatibility

---

## Phase 7: Testing

### 7.1 gpp-api Tests

- [ ] Unit tests for state machine
- [ ] Unit tests for Redis Stream tasks
- [ ] Integration tests for API endpoints
- [ ] Integration tests for OpenZaak client (mocked)

### 7.2 gpp-app Tests

- [ ] Unit tests for authorization logic
- [ ] Integration tests for OIDC flow (mocked)
- [ ] Integration tests for proxy endpoints

### 7.3 E2E Tests

- [ ] Full workflow: create publication → publish → verify in search
- [ ] Auth flow: login → create publication → verify ownership

---

## Phase 8: Docker & Deployment

### 8.1 Dockerfiles

- [ ] Create `services/gpp-api/Dockerfile`:
  ```dockerfile
  FROM python:3.12-slim

  WORKDIR /app

  # Install uv
  RUN pip install uv

  # Copy and install dependencies
  COPY pyproject.toml .
  RUN uv pip install --system -e .

  # Copy source
  COPY src/ src/
  COPY alembic/ alembic/
  COPY alembic.ini .

  # Run migrations and start server
  CMD ["sh", "-c", "alembic upgrade head && uvicorn gpp_api.main:app --host 0.0.0.0 --port 8000"]
  ```

- [ ] Create `services/gpp-app-fastapi/Dockerfile` (similar)

### 8.2 Docker Compose

- [ ] Update `docker-compose.yml`:
  ```yaml
  services:
    gpp-api:
      build: ./services/gpp-api
      ports:
        - "8001:8000"
      environment:
        - DATABASE_URL=postgresql+asyncpg://...
        - REDIS_URL=redis://redis:6379
        - OPENZAAK_URL=http://openzaak:8000
      depends_on:
        - postgres
        - redis

    gpp-api-worker:
      build: ./services/gpp-api
      command: ["python", "-m", "gpp_api.workers"]
      environment:
        - DATABASE_URL=postgresql+asyncpg://...
        - REDIS_URL=redis://redis:6379
      depends_on:
        - postgres
        - redis
        - gpp-api

    gpp-app:
      build: ./services/gpp-app-fastapi
      ports:
        - "8002:8000"
      environment:
        - DATABASE_URL=postgresql+asyncpg://...
        - GPP_API_URL=http://gpp-api:8000
        - WOO_HOO_URL=http://woo-hoo:8000
      depends_on:
        - postgres
        - gpp-api

    caddy:
      image: caddy:latest
      ports:
        - "8080:80"
      volumes:
        - ./docker/caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      depends_on:
        - gpp-api
        - gpp-app
        - woo-hoo
  ```

### 8.3 Kubernetes Manifests

- [ ] Create Helm chart or Kustomize manifests
- [ ] Configure horizontal pod autoscaling for workers
- [ ] Configure Redis Streams persistence

---

## Phase 9: Cleanup

### 9.1 Remove Old Services

- [ ] Remove `services/publicatiebank/` (Django)
- [ ] Remove `services/gpp-app/ODPC.Server/` (C#)
- [ ] Remove `services/gpp-app/ODPC.Test/` (C#)
- [ ] Rename `gpp-app-fastapi` to `gpp-app`
- [ ] Remove nginx configuration
- [ ] Update all documentation

### 9.2 Update CI/CD

- [ ] Update GitHub Actions workflows
- [ ] Remove .NET and Django build steps
- [ ] Add Python lint/test/build steps

---

## Verification Checklist

### API Compatibility
- [ ] All v2 endpoints return same response format
- [ ] All v1 endpoints (via gpp-app) work correctly
- [ ] OpenAPI schema matches existing clients

### Functionality
- [ ] Publication create/read/update/delete works
- [ ] Document upload/download works
- [ ] Publication state transitions work
- [ ] Search indexing works (via Redis Streams)
- [ ] OIDC authentication works
- [ ] User group authorization works
- [ ] woo-hoo metadata generation works

### Performance
- [ ] Response times are equal or better
- [ ] Background tasks process reliably
- [ ] No memory leaks under load

### Observability
- [ ] Structured logging works
- [ ] Health endpoints respond correctly
- [ ] Metrics are exposed (optional)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Data loss during migration | Run both systems in parallel, verify data integrity |
| API incompatibility | Comprehensive API compatibility tests |
| Auth issues | Test OIDC flow thoroughly in staging |
| Task processing failures | Redis Streams provide persistence and retry |
| Performance regression | Load test before cutover |

---

## Timeline Estimate

| Phase | Duration |
|-------|----------|
| Phase 1: Setup | 1 week |
| Phase 2: gpp-api models | 2 weeks |
| Phase 3: Background tasks | 1 week |
| Phase 4: gpp-api endpoints | 2 weeks |
| Phase 5: gpp-app | 2 weeks |
| Phase 6: Migration | 1 week |
| Phase 7: Testing | 1 week |
| Phase 8: Docker/Deploy | 1 week |
| Phase 9: Cleanup | 1 week |
| **Total** | **12 weeks** |
