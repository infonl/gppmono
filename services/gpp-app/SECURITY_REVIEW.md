# Security Review: Metadata Generation Feature

## Summary of Changes

This document reviews the security implications of all changes made to enable the metadata generation feature in the local development environment.

## Changes Made

### 1. Authentication & Authorization (ODPC)

#### DevAutoLoginMiddleware.cs (NEW)
**What it does**: Automatically logs in a "local-dev" user in development mode when OIDC is not configured.

**Security Concerns**:
- ✅ **SAFE FOR PRODUCTION**: Only activates when `IsDevelopment()` is true AND `OIDC_AUTHORITY` is not configured
- ✅ **Production Protected**: In production with OIDC configured, this middleware does nothing
- ⚠️ **Risk**: If accidentally deployed to production with `ASPNETCORE_ENVIRONMENT=Development`, it would bypass authentication
- ✅ **Mitigation**: Environment variable checks prevent this

**Recommendation**: ✅ **SAFE** - Production deployments use OIDC and set environment to Production

#### AuthenticationExtensions.cs
**Changes**:
1. `CookieSecurePolicy.Always` → `CookieSecurePolicy.SameAsRequest`
   - ⚠️ **Risk**: Allows cookies over HTTP in development
   - ✅ **Mitigation**: Only needed for local dev; production should use HTTPS
   - **Recommendation**: ⚠️ **NEEDS REVIEW** - Consider reverting to `.Always` and ensuring production HTTPS

2. AdminPolicy now environment-dependent
   - Dev mode: Any authenticated user is admin
   - Prod mode (with OIDC): Requires actual `odpc-admin` role
   - ✅ **SAFE**: Properly gated by OIDC configuration check

**Recommendation**: ⚠️ **COOKIE SECURITY NEEDS ATTENTION** - Revert `SameAsRequest` change

### 2. ODRC Integration

#### docker/odrc/patches/001_fix_informatieobjecttype_url.py (NEW)
**What it does**: Patches ODRC at runtime to use OpenZaak's Catalogi API URLs instead of ODRC's own URLs.

**Security Concerns**:
- ✅ **Read-only operation**: Only modifies how URLs are constructed
- ✅ **No SQL injection**: Uses ORM (`Service.objects.get()`)
- ✅ **No arbitrary code execution**: Just string replacement in Python source
- ⚠️ **Supply chain risk**: Modifies third-party code at runtime
- ✅ **Idempotent**: Checks if already applied before patching

**Recommendation**: ⚠️ **CONSIDER UPSTREAM** - This is a workaround. Consider:
1. Contributing fix to upstream ODRC project
2. Using configuration-based solution instead of code patching

#### docker/odrc/entrypoint.sh (NEW)
**What it does**: Runs Python patches on container startup.

**Security Concerns**:
- ✅ **Limited scope**: Only runs scripts in `/app/patches/`
- ✅ **Container-local**: Doesn't affect host system
- ⚠️ **Error handling**: Failed patches print warning but don't stop container
- ✅ **Logging**: Clear output about which patches are applied

**Recommendation**: ✅ **ACCEPTABLE** - Consider failing fast if critical patches fail

### 3. Metadata Generation Controller (ODPC)

#### MetadataGenerateController.cs (NEW)
**What it does**: Downloads PDF from ODRC, uploads to woo-hoo service for metadata generation.

**Security Concerns**:

1. **Authentication**:
   - ✅ `/health` endpoint is `[AllowAnonymous]` - reasonable for health checks
   - ✅ `/generate/{documentUuid}` requires authentication (no `[AllowAnonymous]`)

2. **Authorization**:
   - ⚠️ **NO PERMISSION CHECK**: Any authenticated user can generate metadata for any document
   - **Risk**: User A could generate metadata for User B's documents
   - **Recommendation**: ⚠️ **ADD AUTHORIZATION** - Check if user has access to the document

3. **API Key Handling**:
   - ✅ Stored in configuration (not hardcoded)
   - ✅ Passed via Authorization header (not URL params)
   - ⚠️ **Audit headers**: Uses generic "odpc-metadata-service" user
   - **Recommendation**: Consider using actual user ID for audit trail

4. **Input Validation**:
   - ✅ `documentUuid` is typed as `Guid` (prevents injection)
   - ✅ Uses strongly-typed HTTP clients
   - ⚠️ **No size limit**: Downloads entire PDF into memory
   - **Risk**: Large files could cause OOM
   - **Recommendation**: ⚠️ **ADD SIZE LIMIT** - Reject files >50MB

5. **Error Handling**:
   - ⚠️ **Error details exposed**: Returns exception messages to client
   - **Risk**: Could leak internal implementation details
   - **Recommendation**: ⚠️ **SANITIZE ERRORS** - Return generic errors to client, log details server-side

6. **SSRF Protection**:
   - ⚠️ **Configuration-based URLs**: `ODRC_BASE_URL` and `WOO_HOO_BASE_URL` come from config
   - **Risk**: If attacker can modify config, could redirect requests
   - ✅ **Mitigation**: Config is read from environment/appsettings, not user input
   - **Recommendation**: ✅ **ACCEPTABLE** - Config is trusted input

7. **Timeout Configuration**:
   - ✅ Configurable timeouts prevent hanging requests
   - ✅ Defaults (30s health, 120s generate) are reasonable

### 4. Frontend Changes

#### use-generate-metadata.ts (NEW)
**What it does**: Frontend composable to call metadata generation API.

**Security Concerns**:
- ✅ **CSRF Protected**: Uses POST method (ASP.NET Core has CSRF by default)
- ✅ **No sensitive data in localStorage**: Uses reactive refs
- ✅ **Error handling**: Shows generic error messages to user
- ⚠️ **Label matching**: Case-insensitive string matching could cause issues
- ✅ **Fixed**: Added null/undefined filter to prevent errors

**Recommendation**: ✅ **SAFE**

### 5. Docker & Infrastructure

#### docker-compose.yml
**Changes**:
1. OpenZaak: `SENDFILE_BACKEND=django_sendfile.backends.simple`
   - ⚠️ **Performance impact**: Serves files through Django instead of nginx
   - ✅ **Security**: No direct security implications
   - **Recommendation**: ⚠️ **FOR DEV ONLY** - Production should use nginx X-Accel

2. ODRC: Added Celery Redis URLs
   - ✅ **Standard configuration**: No security concerns

3. ODRC: Added patch volumes and entrypoint
   - ⚠️ **Supply chain risk**: Runtime code modification
   - See patch security review above

#### docker/odrc/fixtures/woo-publications.json
**Changes**:
1. Added Catalogus API service configuration
2. Increased timeout from 10s to 60s
   - ✅ **Safe**: Just configuration data

**Insecure Credentials** (PRE-EXISTING):
- ⚠️ `secret: "insecure-yQL9Rzh4eHGVmYx5w3J2gu"`
- ⚠️ `client_id: "woo-publications-dev"`
- **Recommendation**: ⚠️ **ALREADY DOCUMENTED** - These are dev-only credentials

## Critical Security Issues for Production

### HIGH PRIORITY

1. **Authorization Missing in MetadataGenerateController**
   - **Issue**: Any authenticated user can generate metadata for any document
   - **Fix**: Add permission check to verify user has access to document
   ```csharp
   // Check if user has access to this document's publication
   var docResponse = await odrcClient.GetAsync($"{odrcUrl}/api/v2/documenten/{documentUuid}");
   var docData = await docResponse.Content.ReadFromJsonAsync<JsonNode>();
   var publicatieUuid = docData?["publicatie"]?.GetValue<string>();

   // Verify user has access to this publication
   // (implementation depends on your authorization model)
   ```

2. **Cookie Security Policy**
   - **Issue**: `CookieSecurePolicy.SameAsRequest` allows HTTP cookies
   - **Fix**: Change back to `.Always` and ensure production uses HTTPS
   ```csharp
   options.Cookie.SecurePolicy = env.IsDevelopment()
       ? CookieSecurePolicy.SameAsRequest
       : CookieSecurePolicy.Always;
   ```

3. **Error Message Disclosure**
   - **Issue**: Exception messages returned to client
   - **Fix**: Return generic errors, log details
   ```csharp
   catch (Exception ex)
   {
       logger.LogError(ex, "Error generating metadata for document {DocumentUuid}", documentUuid);
       return StatusCode(500, "An error occurred while generating metadata");
   }
   ```

### MEDIUM PRIORITY

4. **File Size Limit**
   - **Issue**: No limit on PDF size
   - **Fix**: Add size check before processing
   ```csharp
   if (pdfBytes.Length > 50 * 1024 * 1024) // 50MB
   {
       return BadRequest("File too large");
   }
   ```

5. **Audit Trail**
   - **Issue**: Generic "odpc-metadata-service" user in audit headers
   - **Fix**: Use actual user ID
   ```csharp
   var userId = User.FindFirst(JwtClaimTypes.PreferredUserName)?.Value ?? "unknown";
   odrcClient.DefaultRequestHeaders.Add("Audit-User-ID", userId);
   ```

### LOW PRIORITY

6. **Runtime Code Patching**
   - **Issue**: ODRC code is modified at runtime
   - **Recommendation**: Contribute fix upstream or use configuration

## Production Deployment Checklist

Before deploying to production:

- [ ] **CRITICAL**: Add authorization check in `MetadataGenerateController.Post()`
- [ ] **CRITICAL**: Change `CookieSecurePolicy` back to `.Always`
- [ ] **CRITICAL**: Sanitize error messages in `MetadataGenerateController`
- [ ] **HIGH**: Add file size limit (50MB) in `MetadataGenerateController`
- [ ] **HIGH**: Use actual user ID in audit headers
- [ ] **MEDIUM**: Revert OpenZaak `SENDFILE_BACKEND` to nginx (or keep if performance is acceptable)
- [ ] **MEDIUM**: Review and secure all API keys and secrets
- [ ] **LOW**: Consider upstreaming ODRC patch
- [ ] Ensure `ASPNETCORE_ENVIRONMENT=Production`
- [ ] Ensure OIDC is properly configured
- [ ] Ensure HTTPS is enforced (load balancer/reverse proxy)
- [ ] Review all environment variables for production values

## Summary

**Current State**: ✅ Safe for **local development only**

**Production Ready**: ⚠️ **NO** - Requires fixes for:
1. Authorization checks
2. Cookie security
3. Error message sanitization
4. File size limits
5. Audit trail improvements

**Risk Level**:
- Development: **LOW** ✅
- Production (as-is): **HIGH** ⚠️
- Production (after fixes): **LOW-MEDIUM** ✅
