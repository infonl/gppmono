# Implementation Summary: Metadata Generation Feature

## Overview

This document summarizes all the issues encountered and fixes applied to get the metadata generation feature working in the local development environment.

## Goal

Enable users to upload a PDF document to a publication in ODPC, then click a "Genereer metadata" button to automatically generate DIWOO-compliant metadata using the woo-hoo AI service.

## Architecture Flow

```
Browser (Vue.js)
    ↓ POST /api/v1/metadata/generate/{documentUuid}
ODPC (.NET Core)
    ↓ GET /api/v2/documenten/{uuid}/download (with audit headers)
ODRC (Django) → nginx proxy
    ↓ proxies to OpenZaak Documents API
OpenZaak (Django)
    ↓ returns PDF file
ODPC receives PDF
    ↓ POST /api/v1/metadata/generate-from-file
woo-hoo (FastAPI)
    ↓ extracts text, calls LLM, returns metadata
ODPC receives metadata
    ↓ returns JSON to browser
Vue.js frontend
    ↓ populates form fields with generated metadata
User saves publication
```

## Issues Encountered and Fixes

### Issue 1: Authentication Failed (Instant Redirect to Login)

**Symptoms**: Opening ODPC redirected immediately to `/login` page

**Root Cause**: Old authentication cookies with wrong encryption keys causing "Unprotect ticket failed" errors

**Attempted Fixes**:
1. ❌ Modified middleware to always recreate cookies (didn't work - SignInAsync only affects future requests)

**Final Fix**: Created `DevAutoLoginMiddleware.cs` that:
- Activates only in Development mode without OIDC
- Sets `context.User` for current request AND creates cookie for future requests
- Auto-creates a "local-dev" user with admin role

**Files Changed**:
- `ODPC.Server/Authentication/DevAutoLoginMiddleware.cs` (new)
- `ODPC.Server/Authentication/AuthenticationExtensions.cs` (added `UseDevAutoLogin()`)
- `ODPC.Server/Program.cs` (called `UseDevAutoLogin()`)

---

### Issue 2: Authorization Failed ("De gebruikersgroep kon niet worden opgeslagen")

**Symptoms**: After authentication worked, creating a gebruikersgroep failed with "Authorization failed"

**Root Cause**: AdminPolicy required `odpc-admin` role, but dev user didn't have it

**Fix**: Made AdminPolicy environment-dependent:
- Dev mode (no OIDC): Requires any authenticated user
- Prod mode (with OIDC): Requires actual `odpc-admin` role

**Files Changed**:
- `ODPC.Server/Authentication/AuthenticationExtensions.cs` (lines 114-127)

---

### Issue 3: User Not in Any Groups (Cannot Create Publication)

**Symptoms**: Publication form shows "user not in any groups" error

**Root Cause**: Database didn't have the "local-dev" user assigned to any gebruikersgroep

**Fix**: Added SQL INSERT to assign local-dev to Groep 1

**Database Changes**:
```sql
INSERT INTO "GebruikersgroepGebruikers" ("GebruikerId", "GebruikersgroepUuid")
VALUES ('local-dev', 'd3da5277-ea07-4921-97b8-e9a181390c76');
```

**Note**: This is applied via database init scripts in docker-compose startup

---

### Issue 4: Document Upload Failed (ODRC Celery Error)

**Symptoms**: Uploading PDF to publication failed with "De metadata bij het document kon niet worden opgeslagen"

**Root Cause**: ODRC couldn't connect to Redis for Celery backend

**Fix**: Added Redis environment variables to ODRC in docker-compose.yml

**Files Changed**:
- `docker-compose.yml` (added `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`)

---

### Issue 5: Document Registration Failed (400 Bad Request from OpenZaak)

**Symptoms**: After Redis fix, upload still failed with:
```
ValidationError: {'informatieobjecttype': [ErrorDetail(string='Voer een geldige URL in.', code='bad-url')]}
```

**Root Cause**: ODRC was sending `informatieobjecttype` URL pointing to its own Catalogi API endpoint (e.g., `http://odrc/catalogi/api/v1/informatieobjecttypen/...`), but OpenZaak's Documents API only accepts URLs from OpenZaak's own Catalogi API.

**Solution**: Created a runtime patch system for ODRC:
1. Created `docker/odrc/patches/` directory with Python patch scripts
2. Created `docker/odrc/entrypoint.sh` to apply patches on container startup
3. Created `001_fix_informatieobjecttype_url.py` that patches ODRC's `Document.register_in_documents_api()` method to query the configured Catalogus API service and construct URLs using OpenZaak's API base URL

**Why Patching?**: ODRC is a third-party Docker image from MaykinMedia. We can't modify the source directly, so we patch it at runtime.

**Files Changed**:
- `docker-compose.yml` (added entrypoint, command, and volumes for patches)
- `docker/odrc/entrypoint.sh` (new)
- `docker/odrc/patches/001_fix_informatieobjecttype_url.py` (new)
- `docker/odrc/patches/README.md` (new - documentation)
- `docker/odrc/fixtures/woo-publications.json` (added Catalogus API service configuration)

**Database Changes**:
- Added `zgw_consumers.service` entry for Catalogus API (pk=3)
- Created two `informatieobjecttype` records in OpenZaak (UUIDs: `a8836b30-8b25-4af6-9b35-e68e4f644c59`, `0f06fded-7e08-437d-9fa2-021841a93842`)

---

### Issue 6: Metadata Generation Failed (403 Forbidden from ODRC)

**Symptoms**: After document upload succeeded, clicking "Genereer metadata" button failed with:
```
Metadata generatie mislukt: Failed to download document from ODRC
```

**Root Cause**: ODPC was sending the Authorization token but missing required audit headers. ODRC's API requires three headers for all requests:
- `Audit-User-ID`
- `Audit-User-Representation`
- `Audit-Remarks`

**Fix**: Modified `MetadataGenerateController.cs` to add the three audit headers before downloading PDFs from ODRC

**Files Changed**:
- `ODPC.Server/Features/Metadata/MetadataGenerateController.cs` (lines 67-70)

---

### Issue 7: Metadata Generation Timeout (60 seconds)

**Symptoms**: Request to ODPC succeeded, PDF downloaded, but then timeout after 60 seconds with no response

**Initial Wrong Analysis**: Thought file size (540KB) was too small for `MIN_UPLOAD_SIZE` (4GB) setting
- ❌ User correctly rejected: "540kb is much smaller than 4gb so that should be fine"

**User Insight**: "why do we need to upload the document? it is uploaded we just need to send it to the woo-hoo app" - Led to breakthrough

**Investigation**: PDFs ARE stored in OpenZaak at `/app/private-media/uploads/`, database has correct paths

**Root Cause Discovery**: OpenZaak was configured to use nginx X-Accel-Redirect:
- Setting: `SENDFILE_BACKEND=django_sendfile.backends.nginx`
- OpenZaak responds with HTTP 200 + `X-Accel-Redirect: /private-media/uploads/...` header
- Expects nginx to intercept this header and serve the actual file
- But there's no nginx in front of OpenZaak in docker-compose
- Result: Response returns 200 with X-Accel-Redirect header, then hangs/timeouts waiting for nginx

**Solution**: Changed OpenZaak's SENDFILE_BACKEND to serve files directly through Django:

**Attempted Fixes**:
1. ❌ `SENDFILE_BACKEND=django.core.files.storage.FileSystemStorage` - Wrong path, still showed X-Accel-Redirect
2. ❌ `SENDFILE_BACKEND=sendfile.backends.development` - Wrong module name (ModuleNotFoundError: No module named 'sendfile')
3. ✅ `SENDFILE_BACKEND=django_sendfile.backends.simple` - Correct! OpenZaak uses django-sendfile2

**Files Changed**:
- `docker-compose.yml` (line 62: `SENDFILE_BACKEND=django_sendfile.backends.simple`)

**Note**: This is for development only. Production should use nginx X-Accel for performance.

---

### Issue 8: Metadata Generation Failed (Text Too Long)

**Symptoms**: woo-hoo service received request but rejected it:
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for DocumentContent
text
  String should have at most 100000 characters
```

**Root Cause**: Extracted text from PDF exceeded 100,000 character limit in woo-hoo's `DocumentContent` model

**Fix**: Increased text length limit from 100,000 to 500,000,000 characters

**Files Changed**:
- `woo-hoo/src/woo_hoo/models/requests.py` (line 30: `max_length=500_000_000`)

---

### Issue 9: Frontend Error ("toLowerCase is undefined")

**Symptoms**: Backend succeeded, but frontend showed:
```
Metadata generatie mislukt: can't access property "toLowerCase", l is undefined
```

**Root Cause**: woo-hoo returned `informatiecategorieen` or `themas` with `undefined` label fields, and frontend tried to call `.toLowerCase()` on them

**Fix**: Added filter to remove undefined/null labels before matching:

```typescript
.filter((label): label is string => !!label) // Filter out undefined/null labels
.map((label) => lijst.find((item) => item.naam.toLowerCase() === label.toLowerCase())?.uuid)
```

**Files Changed**:
- `odpc.client/src/features/publicatie/composables/use-generate-metadata.ts` (line 69)
- Required rebuilding ODPC Docker container to include frontend changes

---

## Final Working State

### What Works Now

1. ✅ Local dev authentication automatically logs in "local-dev" user
2. ✅ User can create publications (assigned to Groep 1)
3. ✅ User can upload PDF documents to publications
4. ✅ PDF is stored in OpenZaak via ODRC with correct informatieobjecttype
5. ✅ "Genereer metadata" button appears when document is attached
6. ✅ Clicking button downloads PDF from ODRC (with audit headers)
7. ✅ PDF is sent to woo-hoo service for processing
8. ✅ woo-hoo extracts text, generates metadata via LLM
9. ✅ Metadata is returned to frontend and populates form fields
10. ✅ User can review and save the generated metadata

### How to Use

1. Start all services: `docker-compose up -d`
2. Wait ~30 seconds for patches to apply and services to be ready
3. Open http://localhost:62230
4. Navigate to a publication
5. Upload a PDF document
6. Click "Genereer metadata" button
7. Wait ~17 seconds for processing
8. Review generated metadata in form fields
9. Click "Opslaan als concept" or "Publiceren" to save

### Services & Ports

- **ODPC UI**: http://localhost:62230
- **ODRC UI**: http://localhost:8000
- **ODRC API**: http://localhost:8002 (via nginx)
- **OpenZaak UI**: http://localhost:8001
- **woo-hoo** (not exposed externally, ODPC connects via host.docker.internal:8003)

### Default Credentials

- Username: `admin`
- Password: `admin`

---

## Files Changed Summary

### New Files Created (11)

1. `ODPC.Server/Authentication/DevAutoLoginMiddleware.cs` - Auto-login for dev mode
2. `ODPC.Server/Features/Metadata/MetadataGenerateController.cs` - Metadata generation API
3. `odpc.client/src/features/publicatie/composables/use-generate-metadata.ts` - Frontend composable
4. `odpc.client/src/features/publicatie/composables/__tests__/use-generate-metadata.test.ts` - Tests
5. `docker/odrc/entrypoint.sh` - Patch application script
6. `docker/odrc/patches/001_fix_informatieobjecttype_url.py` - ODRC URL fix patch
7. `docker/odrc/patches/README.md` - Patch documentation
8. `FIXES.md` - Comprehensive fix documentation
9. `METADATA_GENERATION.md` - Feature documentation (created earlier)
10. `Makefile` - Development helpers (created earlier)
11. `docker/nginx/nginx.conf` - Nginx config for ODRC proxy

### Modified Files (22)

1. `ODPC.Server/Authentication/AuthenticationExtensions.cs` - AdminPolicy, cookie security, UseDevAutoLogin
2. `ODPC.Server/Program.cs` - Add UseDevAutoLogin middleware
3. `ODPC.Server/appsettings.json` - Add WOO_HOO_BASE_URL config
4. `odpc.client/src/config.ts` - Add odpcApiUrl config
5. `odpc.client/src/features/publicatie/PublicatieDetails.vue` - Add metadata generation UI
6. `docker-compose.yml` - SENDFILE_BACKEND, ODRC entrypoint, patches, Celery Redis
7. `docker-compose.override.yml` - Local dev overrides
8. `docker/odrc/fixtures/woo-publications.json` - Add Catalogus API service, increase timeout
9-22. Various other minor changes and test updates

### Database Changes

- Added `zgw_consumers.service` for Catalogus API (via fixtures)
- Added `informatieobjecttype` records in OpenZaak
- Assigned "local-dev" user to Groep 1

---

## Key Learnings

1. **Third-Party Integration Complexity**: Integrating three separate systems (ODPC, ODRC, OpenZaak) revealed incompatibilities that required creative solutions (runtime patching)

2. **URL Construction Matters**: OpenZaak is strict about accepting informatieobjecttype URLs only from its own API, not from ODRC's proxy endpoint

3. **Audit Headers Are Required**: ODRC enforces audit trail headers on all API requests

4. **File Serving Configuration**: The nginx X-Accel-Redirect pattern requires nginx to be present; without it, downloads hang

5. **Development vs Production**: Many fixes are dev-specific and need different approaches for production

6. **User Feedback is Critical**: User correctly redirected focus when I went down wrong paths (e.g., MIN_UPLOAD_SIZE analysis)

---

## Next Steps for Production

See [SECURITY_REVIEW.md](SECURITY_REVIEW.md) for:
- Critical security issues to fix
- Production deployment checklist
- Risk assessment
- Recommendations for each change

**TL;DR Production Needs**:
1. Add authorization checks (verify user can access document)
2. Fix cookie security policy
3. Sanitize error messages
4. Add file size limits
5. Improve audit trail
6. Consider upstreaming ODRC patch
