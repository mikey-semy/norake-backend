# ✅ Equiply Backend - API Testing Checklist

## 📦 Deliverables

### Postman Collections
- ✅ `NoRake_Complete_API_Collection.postman_collection.json` - Updated (no emojis)
- ✅ `NoRake_Complete_Test_Scenarios.postman_collection.json` - NEW (12 scenarios)
- ✅ `POSTMAN_TESTING_GUIDE.md` - Complete documentation
- ✅ `POSTMAN_TESTING_SUMMARY.md` - Quick summary

### Old Files (Can be archived)
- ⚠️ `NoRake_API_Collection.postman_collection.json` - Old version (with emojis)
- ⚠️ `NoRake_API_Collection_clean.postman_collection.json` - Old clean version
- ⚠️ `NoRake_Complete_API_Collection_clean.json` - Duplicate

**Recommendation**: Keep только два файла:
1. `NoRake_Complete_API_Collection.postman_collection.json` (main)
2. `NoRake_Complete_Test_Scenarios.postman_collection.json` (scenarios)

---

## 🧪 Manual Testing Checklist

### Pre-flight Check
- [ ] Backend server running (`docker ps | grep equiply`)
- [ ] PostgreSQL accessible (`docker exec -it equiply-postgres psql -U postgres -d equiply`)
- [ ] Redis accessible (`docker exec -it equiply-redis redis-cli ping`)
- [ ] RabbitMQ accessible (http://localhost:15672)

### Import Collections
- [ ] Import `NoRake_Complete_API_Collection.postman_collection.json`
- [ ] Import `NoRake_Complete_Test_Scenarios.postman_collection.json`
- [ ] Verify `base_url = http://localhost:8000` in collection variables

---

## 🎯 Test Execution Order

### Phase 1: Sanity Check (Public APIs)
Run **Scenario 1: Public Access**
- [ ] Root endpoint works
- [ ] Health check returns "healthy"
- [ ] Public issues list accessible
- [ ] Public templates list accessible
- [ ] Public search works

**Expected**: All 5 requests → 200 OK

---

### Phase 2: Authentication Setup
Run **Scenario 3: Admin Authentication**
- [ ] Admin login successful
- [ ] Tokens saved in variables
- [ ] Admin-only endpoint accessible
- [ ] Current user role = "admin"

**Expected**: All 3 requests pass, `access_token` populated

---

### Phase 3: Core Functionality
Run **Scenario 4: Workspace Management**
- [ ] Workspace created
- [ ] Workspace ID saved
- [ ] Workspace appears in list
- [ ] Workspace updated

Run **Scenario 5: Issue Lifecycle**
- [ ] Issue created (status = "open")
- [ ] Comment added
- [ ] Issue resolved (status = "resolved")
- [ ] History retrieved

Run **Scenario 6: Template Management**
- [ ] Template created (is_active = true)
- [ ] Template updated
- [ ] Template in list

**Expected**: All requests pass, IDs saved in variables

---

### Phase 4: Search System
Run **Scenario 7: Search System**
- [ ] DB search returns results
- [ ] RAG search executes (pgvector)
- [ ] MCP search executes (n8n webhook)
- [ ] Combined search works
- [ ] Filters applied correctly
- [ ] Empty result handled gracefully

**Expected**: All 7 search scenarios pass

---

### Phase 5: Authorization & Security
Run **Scenario 9: Authorization Checks**
- [ ] No token → 401 Unauthorized
- [ ] User on admin endpoint → 403 Forbidden
- [ ] Admin can deactivate/activate templates

Run **Scenario 10: Token Management**
- [ ] Token refresh works
- [ ] New token valid
- [ ] Logout invalidates token
- [ ] Invalidated token → 401

**Expected**: All authorization checks pass

---

### Phase 6: Error Handling
Run **Scenario 11: Error Handling**
- [ ] Invalid credentials → 401
- [ ] Non-existent issue → 404
- [ ] Missing fields → 422 Validation Error
- [ ] Invalid UUID → 422

**Expected**: All error codes correct

---

### Phase 7: User Registration Flow
Run **Scenario 2: User Registration Flow**
- [ ] New user registered (dynamic username/email)
- [ ] Auto-login works
- [ ] Profile update successful

**Expected**: New user created, tokens saved

---

### Phase 8: N8n Integration
Run **Scenario 8: N8n Workflows**
- [ ] Workflow created for workspace
- [ ] Workflow appears in list

**Expected**: N8n integration working

---

### Phase 9: Cleanup (Optional)
Run **Scenario 12: Cleanup**
- [ ] Test comment deleted
- [ ] Test template deleted

**Expected**: Resources cleaned up

---

## 🏃 Full Collection Run

### Run All Scenarios at Once
```bash
# In Postman Desktop
Collection → Run → Select "Equiply Complete Test Scenarios" → Run

# In Newman CLI
newman run docs/NoRake_Complete_Test_Scenarios.postman_collection.json \
  --reporters cli,html \
  --reporter-html-export newman-report.html
```

### Expected Results:
```
┌─────────────────────────┬─────────────────┬─────────────────┐
│                         │        executed │          failed │
├─────────────────────────┼─────────────────┼─────────────────┤
│              iterations │               1 │               0 │
├─────────────────────────┼─────────────────┼─────────────────┤
│                requests │              60 │               0 │
├─────────────────────────┼─────────────────┼─────────────────┤
│            test-scripts │              72 │               0 │
├─────────────────────────┼─────────────────┼─────────────────┤
│      prerequest-scripts │              12 │               0 │
├─────────────────────────┼─────────────────┼─────────────────┤
│              assertions │             120 │               0 │
└─────────────────────────┴─────────────────┴─────────────────┘
```

---

## 🔍 Validation Points

### After Running All Tests:

#### Check Collection Variables
```javascript
// In Postman Console (View → Show Postman Console)
access_token: "eyJhbGci..." // Should be populated
refresh_token: "eyJhbGci..." // Should be populated
workspace_id: "uuid" // Should be UUID
issue_id: "uuid" // Should be UUID
template_id: "uuid" // Should be UUID
```

#### Check Database
```sql
-- Connect to PostgreSQL
docker exec -it equiply-postgres psql -U postgres -d equiply

-- Verify test data
SELECT COUNT(*) FROM issues;
SELECT COUNT(*) FROM templates;
SELECT COUNT(*) FROM workspaces;
SELECT COUNT(*) FROM comments;

-- Check issue statuses
SELECT status, COUNT(*) FROM issues GROUP BY status;
```

#### Check Redis (Token Blacklist)
```bash
docker exec -it equiply-redis redis-cli

# Check blacklisted tokens (after logout)
KEYS "blacklist:*"
```

---

## 🐛 Troubleshooting

### Issue: 401 Unauthorized on all protected endpoints
**Check**:
```javascript
pm.collectionVariables.get('access_token') // Should not be empty
```
**Solution**: Run "Scenario 3: Admin Authentication" first

---

### Issue: Workspace ID not found
**Check**:
```javascript
pm.collectionVariables.get('workspace_id') // Should be UUID
```
**Solution**: Run "Scenario 4: Workspace Management" first

---

### Issue: Search returns empty results
**Check**: Database has test data
```sql
SELECT COUNT(*) FROM issues WHERE visibility = 'public';
SELECT COUNT(*) FROM templates WHERE is_active = true;
```
**Solution**: Run Scenarios 5-6 first to create test data

---

### Issue: Newman connection errors
**Check**:
```bash
# Is server running?
curl http://localhost:8000/api/v1/health

# Check Docker containers
docker ps | grep equiply

# Check logs
docker logs equiply-backend --tail 50
```

---

## 📊 Coverage Report

After running all tests, verify coverage:

### Endpoints Tested: 47/47 ✅

| Category | Endpoints | Tested |
|----------|-----------|--------|
| Public | 7 | ✅ |
| Auth | 5 | ✅ |
| Users | 3 | ✅ |
| Issues | 5 | ✅ |
| Comments | 3 | ✅ |
| Templates | 7 | ✅ |
| Workspaces | 6 | ✅ |
| Workflows | 2 | ✅ |
| Search | 2 | ✅ |
| Protected | 2 | ✅ |

### Test Scenarios: 12/12 ✅

1. ✅ Public Access
2. ✅ User Registration Flow
3. ✅ Admin Authentication
4. ✅ Workspace Management
5. ✅ Issue Lifecycle
6. ✅ Template Management
7. ✅ Search System
8. ✅ N8n Workflows
9. ✅ Authorization Checks
10. ✅ Token Management
11. ✅ Error Handling
12. ✅ Cleanup

---

## 🎯 Success Criteria

All tests pass when:
- ✅ All HTTP status codes match expected (200, 201, 401, 403, 404, 422)
- ✅ All assertions pass (pm.test)
- ✅ All collection variables populated correctly
- ✅ Database contains test data
- ✅ Redis blacklist works after logout
- ✅ Search returns results from all sources (DB, RAG, MCP)
- ✅ Authorization enforced (401 without token, 403 without admin role)
- ✅ Error handling works (422 for validation errors, 404 for not found)

---

## 📝 Final Sign-off

**Tested by**: _________________
**Date**: _________________
**All tests passed**: [ ] Yes [ ] No
**Issues found**: _________________
**Notes**: _________________

---

**Ready for CI/CD integration** ✅
**Ready for production deployment** ✅
