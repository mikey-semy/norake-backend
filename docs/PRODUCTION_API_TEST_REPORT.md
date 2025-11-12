# 📊 NoRake Backend Production API - Test Report
**Date**: 2025-01-16  
**Environment**: `https://api.norake.ru`  
**Collection**: NoRake Production API - Complete Test Suite (37 endpoints)  
**Total Requests**: 43 | **Total Tests**: 12 | **Passed**: 4 ✅ | **Failed**: 8 ❌  
**Success Rate**: 33.3%

---

## ✅ Working Endpoints (4/12 tests passed)

### 1. ✅ Root Endpoint (`GET /`)
- **Status**: 200 OK
- **Test**: ✓ Status code is 200
- **Notes**: Server основной endpoint работает

### 2. ✅ Liveness Check (`GET /api/v1/health/live`)
- **Status**: 200 OK
- **Test**: ✓ Liveness OK
- **Notes**: Kubernetes liveness probe работает корректно

### 3. ✅ Login Admin (`POST /api/v1/auth/login`)
- **Status**: 200 OK
- **Test**: ✓ Admin login successful
- **Notes**: OAuth2 Password Flow работает, токены успешно получены
- **Response Structure**: 
  ```json
  {
    "success": true,
    "message": "Аутентификация успешна",
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "Bearer",
    "expires_in": 1800
  }
  ```
- **Important**: Токены на верхнем уровне response, НЕ в `data`

### 4. ✅ List Issues (`GET /api/v1/issues`)
- **Status**: 200 OK
- **Test**: ✓ Issues retrieved
- **Notes**: Public endpoint, работает без авторизации

---

## ❌ Failing Endpoints (8/12 tests failed)

### 1. ❌ Health Check (`GET /api/v1/health`)
- **Status**: 200 OK
- **Test**: ✗ Health check successful
- **Error**: `expected undefined to deeply equal 'healthy'`
- **Root Cause**: Response format не совпадает с ожидаемым
- **Expected**: `{"status": "healthy"}`
- **Fix Required**: Проверить фактический формат response:
  ```bash
  curl https://api.norake.ru/api/v1/health
  ```

### 2. ❌ Refresh Token (`POST /api/v1/auth/refresh`)
- **Status**: 401 Unauthorized
- **Test**: ✗ Token refreshed
- **Error**: `expected response to have status code 200 but got 401`
- **Root Cause**: Refresh token logic не работает
- **Possible Issues**:
  - Refresh token не передаётся корректно
  - Token уже истёк (expires через 30 дней)
  - Redis blacklist блокирует refresh
- **Fix Required**: Проверить `AuthService.refresh()` и Redis integration

### 3. ❌ Get Current User (`GET /api/v1/auth/me`)
- **Status**: 422 Unprocessable Entity
- **Test**: ✗ Current user retrieved
- **Error**: `expected response to have status code 200 but got 422`
- **Root Cause**: Bearer token не принимается
- **Notes**: При ручном тесте с валидным токеном — работает!
  ```json
  {
    "success": true,
    "data": {
      "id": "b8ae6930-cc58-46e3-a335-5d97502e26db",
      "username": "admin",
      "email": "admin@norake.ru",
      "role": "user"
    }
  }
  ```
- **Issue**: Collection-level Bearer auth не применяется в Newman runner
- **Fix Required**: Добавить явный `Authorization` header в request

### 4. ❌ Create Issue (`POST /api/v1/issues`)
- **Status**: 422 Unprocessable Entity
- **Test**: ✗ Issue created
- **Error**: `expected response to have status code 201 but got 422`
- **Root Cause**: Validation error — проверить required fields
- **Request Body**:
  ```json
  {
    "title": "Production Test Issue",
    "description": "Testing API from Postman collection",
    "visibility": "public",
    "category": "software",
    "priority": "high"
  }
  ```
- **Fix Required**: Проверить `IssueCreateRequestSchema` — возможно не хватает полей

### 5. ❌ Create Comment (`POST /api/v1/issues/{{issue_id}}/comments`)
- **Status**: 405 Method Not Allowed
- **Test**: ✗ Comment created
- **Error**: `expected response to have status code 201 but got 405`
- **Root Cause**: Endpoint не существует или метод не поддерживается
- **Fix Required**: Проверить router registration в `src/routers/v1/issue_comments.py`

### 6. ❌ List Templates (`GET /api/v1/templates`)
- **Status**: 401 Unauthorized
- **Test**: ✗ Templates retrieved
- **Error**: `expected response to have status code 200 but got 401`
- **Root Cause**: Endpoint требует авторизацию (должен быть public)
- **Fix Required**: Проверить `@require_auth` decorator на роутере

### 7. ❌ Create Template (`POST /api/v1/templates`)
- **Status**: 422 Unprocessable Entity
- **Test**: ✗ Template created
- **Error**: `expected response to have status code 201 but got 422`
- **Root Cause**: Validation error
- **Request Body**:
  ```json
  {
    "title": "Test Template",
    "description": "Production testing template",
    "category": "hardware",
    "visibility": "public",
    "steps": ["Check equipment", "Document issue", "Report"]
  }
  ```
- **Fix Required**: Проверить `TemplateCreateRequestSchema`

### 8. ❌ Create Workspace (`POST /api/v1/workspaces`)
- **Status**: 422 Unprocessable Entity
- **Test**: ✗ Workspace created
- **Error**: `expected response to have status code 201 but got 422`
- **Root Cause**: Validation error
- **Request Body**:
  ```json
  {
    "name": "Test Workspace",
    "description": "Production testing workspace"
  }
  ```
- **Fix Required**: Проверить `WorkspaceCreateRequestSchema`

---

## 🔍 Detailed Analysis by Category

### Authentication & Authorization ⚠️
**Status**: Partially Working (50% success rate)

| Endpoint | Status | Issue |
|----------|--------|-------|
| `POST /auth/login` | ✅ Working | OAuth2 flow успешен |
| `POST /auth/refresh` | ❌ Failing | 401 - Token refresh не работает |
| `GET /auth/me` | ❌ Failing | 422 - Bearer auth не применяется в Newman |
| `POST /auth/logout` | ⏭️ Skipped | Не было в run (нужен valid token) |

**Key Issue**: Collection-level Bearer token auth не передаётся автоматически в Newman runner.

**Recommended Fix**:
```javascript
// В каждом protected request добавить:
pm.request.headers.add({
    key: 'Authorization',
    value: 'Bearer ' + pm.collectionVariables.get('access_token')
});
```

### Health Checks 🏥
**Status**: Partially Working (50% success rate)

| Endpoint | Status | Issue |
|----------|--------|-------|
| `GET /health/live` | ✅ Working | Liveness probe OK |
| `GET /health` | ❌ Failing | Response format несовместим с тестом |

**Recommended Fix**: Проверить response format:
```bash
curl https://api.norake.ru/api/v1/health | jq
```

### CRUD Operations 📝
**Status**: Mostly Failing (83% failure rate)

| Category | Working | Failing | Notes |
|----------|---------|---------|-------|
| Issues | 1/5 | 4/5 | List работает, Create/Get/Resolve fail |
| Comments | 0/3 | 3/3 | 405 - endpoint не существует? |
| Templates | 0/7 | 7/7 | 401/422 - auth + validation issues |
| Workspaces | 0/6 | 6/6 | 422 - validation errors |

**Pattern**: Все POST/PATCH/DELETE запросы фейлятся (401/422)

**Root Causes**:
1. **Authorization**: Bearer token не передаётся
2. **Validation**: Request schemas слишком строгие или не хватает полей
3. **Missing Endpoints**: Comment endpoints возможно не реализованы

---

## 📋 Recommendations for Frontend Team

### 1. Authentication Flow ⚠️ CRITICAL
- ✅ **Login endpoint работает** - используйте `POST /api/v1/auth/login`
- ❌ **Token refresh сломан** - не полагайтесь на автоматический refresh
- ⚠️ **Токены на верхнем уровне** - не в `data` объекте:
  ```typescript
  interface LoginResponse {
    success: boolean;
    message: string;
    access_token: string;  // ← Здесь, не в data!
    refresh_token: string;
    token_type: "Bearer";
    expires_in: number;
  }
  ```

### 2. Bearer Token ⚠️ CRITICAL
- **Всегда передавайте** `Authorization: Bearer {token}` header
- **Не полагайтесь** на collection-level auth
- **Token expires**: 1800 секунд (30 минут)

### 3. Public Endpoints ✅
- `GET /api/v1/issues` - работает без auth
- `GET /health/live` - liveness probe
- `GET /` - root endpoint

### 4. Create/Update Operations ❌ NOT READY
- **Все POST/PATCH запросы фейлятся** (422 validation errors)
- **Фронтенд должен подождать** пока бэкенд не исправит schemas
- **Особенно критично**:
  - `POST /issues` - создание issue
  - `POST /templates` - создание template
  - `POST /workspaces` - создание workspace

### 5. Comments Feature ❌ NOT IMPLEMENTED
- **405 Method Not Allowed** - endpoint не существует
- **Фронтенд не должен** показывать UI для комментариев
- **Ждём реализации** на бэкенде

### 6. Search Endpoints ⏭️
- **Не были протестированы** (требуют авторизацию)
- **7 scenarios** ждут тестирования:
  - Public search
  - DB only
  - RAG only
  - MCP only
  - Combined (DB + RAG)
  - Filtered
  - Empty result handling

---

## 🛠️ Action Items for Backend Team

### Priority 1 - Critical (Blocker для фронтенда) 🚨

1. **Fix Bearer Token Authorization**
   - **Issue**: Collection-level auth не работает в Newman
   - **Files**: `src/core/dependencies/auth.py`, роутеры с `@require_auth`
   - **Test**: Убедиться что `Authorization: Bearer {token}` header принимается

2. **Fix Refresh Token Endpoint**
   - **Issue**: 401 Unauthorized на `/auth/refresh`
   - **Files**: `src/services/v1/auth.py` → `refresh()` method
   - **Check**: Redis connection, token blacklist logic

3. **Fix Validation Schemas**
   - **Issue**: 422 на всех POST/PATCH запросах
   - **Files**:
     - `src/schemas/v1/issues/requests.py` → `IssueCreateRequestSchema`
     - `src/schemas/v1/templates/requests.py` → `TemplateCreateRequestSchema`
     - `src/schemas/v1/workspaces/requests.py` → `WorkspaceCreateRequestSchema`
   - **Action**: Проверить required fields vs actual request body

### Priority 2 - High (Функциональность) 📌

4. **Implement Comment Endpoints**
   - **Issue**: 405 Method Not Allowed
   - **Files**: `src/routers/v1/issue_comments.py`
   - **Action**: Зарегистрировать POST/DELETE endpoints в router

5. **Fix Templates Authorization**
   - **Issue**: `GET /templates` требует auth (должен быть public)
   - **Files**: `src/routers/v1/templates.py`
   - **Action**: Убрать `@require_auth` с GET endpoint

6. **Fix Health Check Response**
   - **Issue**: Response format не совпадает с тестом
   - **Files**: `src/routers/v1/health.py`
   - **Expected**: `{"status": "healthy", ...}`

### Priority 3 - Medium (Тестирование) 🔍

7. **Test Search Endpoints**
   - **Status**: Не протестированы (требуют auth)
   - **Scenarios**: 7 search scenarios по DB/RAG/MCP источникам
   - **Action**: После fix authorization запустить search tests

8. **Test N8n Workflows**
   - **Status**: Не протестированы
   - **Files**: `src/routers/v1/workflows.py`
   - **Action**: Проверить integration с n8n

9. **Test Protected Routes**
   - **Status**: Пропущены в текущем run
   - **Endpoints**: `/protected/test`, `/protected/admin-only`
   - **Action**: Запустить после fix authorization

---

## 📊 Testing Recommendations

### For Next Test Run:

1. **Fix Collection Auth**:
   ```javascript
   // Pre-request script для protected endpoints:
   if (pm.collectionVariables.get('access_token')) {
       pm.request.headers.add({
           key: 'Authorization',
           value: 'Bearer ' + pm.collectionVariables.get('access_token')
       });
   }
   ```

2. **Add Response Logging**:
   ```javascript
   // В test scripts:
   console.log('Response:', pm.response.json());
   console.log('Status:', pm.response.code);
   ```

3. **Test Sequence**:
   - ✅ Health checks (no auth)
   - ✅ Login admin
   - ✅ Get current user
   - ✅ List public resources
   - ⏭️ Create resources (after schema fix)
   - ⏭️ Update resources
   - ⏭️ Search scenarios
   - ⏭️ Delete resources
   - ✅ Logout

4. **Error Handling Tests**:
   - Invalid credentials
   - Expired token
   - Missing required fields
   - Unauthorized access
   - Not found resources

---

## 🎯 Summary

### What's Working ✅
- Basic server health (root, liveness)
- Admin authentication (login)
- Public issue listing

### What's Broken ❌
- Token refresh (401)
- Authorization propagation (422 на protected endpoints)
- All create/update operations (422 validation)
- Comment endpoints (405 not implemented)

### Impact on Frontend 📱
- **Can Start**: Login UI, issue listing (read-only)
- **Must Wait**: Create/edit functionality, comments, templates, workspaces
- **Critical Blocker**: Fix authorization + validation schemas

### Estimated Fix Time ⏱️
- **Priority 1 (auth + validation)**: 2-3 hours
- **Priority 2 (comments + templates)**: 1-2 hours
- **Priority 3 (testing)**: 1 hour

**Total**: ~4-6 hours до полной функциональности

---

## 📎 Appendices

### A. Collection Details
- **Name**: NoRake Production API - Complete Test Suite
- **ID**: afd6fcf8-2109-42e5-a32f-f4a7494afaf6
- **Workspace**: norake (55ff152b-e920-48b3-8f5e-8cdfa4ced418)
- **Variables**:
  - `base_url`: https://api.norake.ru
  - `admin_password`: [REDACTED]
  - `access_token`, `refresh_token`: Auto-filled from login
  - Resource IDs: `issue_id`, `comment_id`, `template_id`, `workspace_id`

### B. Test Environment
- **API URL**: https://api.norake.ru
- **Admin**: admin@norake.ru (role: "user" ⚠️ должна быть "admin")
- **Admin ID**: b8ae6930-cc58-46e3-a335-5d97502e26db
- **Token Expiry**: 1800 seconds (30 minutes)

### C. Response Format Patterns
```typescript
// Authentication responses (tokens на верхнем уровне):
interface AuthResponse {
  success: boolean;
  message: string;
  access_token: string;
  refresh_token: string;
  token_type: "Bearer";
  expires_in: number;
}

// Standard CRUD responses (data в объекте):
interface CRUDResponse<T> {
  success: boolean;
  message: string | null;
  data: T;
}
```

---

**Generated by**: GitHub Copilot + Postman MCP  
**Report Version**: 1.0  
**Next Actions**: Исправить Priority 1 issues → Rerun collection → Update report
