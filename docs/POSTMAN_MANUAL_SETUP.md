# 🔧 Ручная настройка Postman Collection

## ✅ Что уже сделано автоматически

- ✅ Коллекция создана: **"Equiply Production API Tests"**
- ✅ 9 запросов добавлены с правильными именами (эмодзи для удобства)
- ✅ HTTP методы установлены (GET/POST)
- ✅ Переменные коллекции настроены:
  - `base_url` = `https://api.equiply.ru`
  - `admin_username` = `admin`
  - `admin_password` = `admin123`
  - Пустые переменные для автосохранения: `access_token`, `workspace_id`, `issue_id`, etc.
- ✅ Bearer auth на уровне коллекции (использует `{{access_token}}`)

## ⚠️ Что нужно добавить вручную

Postman API не позволяет программно устанавливать URL, body и test scripts через `updateCollectionRequest`.

### Открой коллекцию в Postman Web:
https://web.postman.co/workspace/equiply~55ff152b-e920-48b3-8f5e-8cdfa4ced418

---

## 📋 Настройка каждого запроса

### 1️⃣ Admin Login

**URL:**
```
{{base_url}}/api/v1/auth/login
```

**Body** (x-www-form-urlencoded):
```
username: {{admin_username}}
password: {{admin_password}}
```

**Tests:**
```javascript
pm.test('✅ Admin login successful', () => {
    pm.response.to.have.status(200);
    const json = pm.response.json();
    pm.expect(json.success).to.be.true;

    const data = json.data;
    pm.collectionVariables.set('access_token', data.access_token);
    pm.collectionVariables.set('refresh_token', data.refresh_token);

    console.log('🔑 Access token saved:', data.access_token.substring(0, 20) + '...');
    console.log('🔄 Refresh token saved');
});
```

**Auth:** No Auth (этот запрос сам получает токен)

---

### Health Check

**URL:**
```
{{base_url}}/api/v1/health
```

**Tests:**
```javascript
pm.test('✅ Health check passed', () => {
    pm.response.to.have.status(200);
    const json = pm.response.json();
    pm.expect(json.success).to.be.true;

    const data = json.data;
    pm.expect(data.app).to.eql('ok');
    pm.expect(data.db).to.eql('ok');

    console.log('💚 App status:', data.app);
    console.log('💾 Database status:', data.db);
});
```

**Auth:** No Auth (публичный эндпойнт)

---

### 2️⃣ List Public Issues

**URL:**
```
{{base_url}}/api/v1/public/issues
```

**Tests:**
```javascript
pm.test('✅ Public issues retrieved', () => {
    pm.response.to.have.status(200);
    const json = pm.response.json();
    pm.expect(json.success).to.be.true;

    const data = json.data;
    pm.expect(data).to.be.an('array');

    console.log('📋 Total public issues:', data.length);
    if (data.length > 0) {
        console.log('📝 First issue:', data[0].title);
    }
});
```

**Auth:** No Auth (публичный эндпойнт)

---

### 3️⃣ List Public Templates

**URL:**
```
{{base_url}}/api/v1/public/templates
```

**Tests:**
```javascript
pm.test('✅ Public templates retrieved', () => {
    pm.response.to.have.status(200);
    const json = pm.response.json();
    pm.expect(json.success).to.be.true;

    const data = json.data;
    pm.expect(data).to.be.an('array');

    console.log('📄 Total public templates:', data.length);
    if (data.length > 0) {
        console.log('📝 First template:', data[0].name);
    }
});
```

**Auth:** No Auth (публичный эндпойнт)

---

### 4️⃣ Create Workspace

**URL:**
```
{{base_url}}/api/v1/workspaces
```

**Body** (raw JSON):
```json
{
  "name": "Test Workspace {{$timestamp}}",
  "description": "Created via Postman MCP production test"
}
```

**Tests:**
```javascript
pm.test('✅ Workspace created', () => {
    pm.response.to.have.status(201);
    const json = pm.response.json();
    pm.expect(json.success).to.be.true;

    const data = json.data;
    pm.collectionVariables.set('workspace_id', data.id);

    console.log('🏢 Workspace ID:', data.id);
    console.log('📛 Workspace name:', data.name);
});
```

**Auth:** Inherit from parent (использует Bearer token)

---

### 5️⃣ Create Issue

**URL:**
```
{{base_url}}/api/v1/issues
```

**Body** (raw JSON):
```json
{
  "title": "Production Test Issue {{$timestamp}}",
  "description": "Testing issue creation from Postman MCP",
  "status": "open",
  "priority": "medium",
  "category": "equipment",
  "visibility": "public",
  "workspace_id": "{{workspace_id}}"
}
```

**Tests:**
```javascript
pm.test('✅ Issue created', () => {
    pm.response.to.have.status(201);
    const json = pm.response.json();
    pm.expect(json.success).to.be.true;

    const data = json.data;
    pm.collectionVariables.set('issue_id', data.id);
    pm.expect(data.status).to.eql('open');

    console.log('📋 Issue ID:', data.id);
    console.log('📝 Issue title:', data.title);
    console.log('🔴 Status:', data.status);
});
```

**Auth:** Inherit from parent

---

### 6️⃣ Add Issue Comment

**URL:**
```
{{base_url}}/api/v1/issues/{{issue_id}}/comments
```

**Body** (raw JSON):
```json
{
  "content": "Test comment from Postman MCP",
  "parent_id": null
}
```

**Tests:**
```javascript
pm.test('✅ Comment added', () => {
    pm.response.to.have.status(201);
    const json = pm.response.json();
    pm.expect(json.success).to.be.true;

    const data = json.data;
    pm.collectionVariables.set('comment_id', data.id);

    console.log('💬 Comment ID:', data.id);
    console.log('📝 Content:', data.content);
});
```

**Auth:** Inherit from parent

---

### 7️⃣ Create Template

**URL:**
```
{{base_url}}/api/v1/templates
```

**Body** (raw JSON):
```json
{
  "name": "Test Template {{$timestamp}}",
  "description": "Production test template",
  "category": "equipment",
  "fields": [
    {"name": "serial_number", "type": "string", "required": true},
    {"name": "model", "type": "string", "required": false}
  ],
  "is_active": true,
  "visibility": "public"
}
```

**Tests:**
```javascript
pm.test('✅ Template created', () => {
    pm.response.to.have.status(201);
    const json = pm.response.json();
    pm.expect(json.success).to.be.true;

    const data = json.data;
    pm.collectionVariables.set('template_id', data.id);
    pm.expect(data.is_active).to.be.true;

    console.log('📄 Template ID:', data.id);
    console.log('📝 Template name:', data.name);
    console.log('✅ Active:', data.is_active);
});
```

**Auth:** Inherit from parent

---

### 8️⃣ Search All Sources

**URL:**
```
{{base_url}}/api/v1/search
```

**Body** (raw JSON):
```json
{
  "query": "equipment",
  "sources": ["db", "rag", "mcp"],
  "limit": 10
}
```

**Tests:**
```javascript
pm.test('✅ Search executed', () => {
    pm.response.to.have.status(200);
    const json = pm.response.json();
    pm.expect(json.success).to.be.true;

    const data = json.data;
    pm.expect(data).to.have.property('results');

    console.log('🔍 Total results:', data.results.length);
    console.log('📊 Sources used:', Object.keys(data.results_by_source || {}));

    if (data.results_by_source) {
        Object.entries(data.results_by_source).forEach(([source, results]) => {
            console.log(`  - ${source}: ${results.length} results`);
        });
    }
});
```

**Auth:** Inherit from parent

---

## 🚀 Порядок запуска

1. **Сначала запусти "1️⃣ Admin Login"** → сохранит `access_token`
2. **Затем все остальные** (они автоматически используют сохранённый токен)

Или запусти всю коллекцию через **"Run collection"** → они выполнятся по порядку.

---

## ⚡ Быстрый способ (альтернатива)

Вместо ручной настройки можешь **импортировать готовый файл**:

**Файл:** `docs/NoRake_Production_API_Import.postman_collection.json`

1. Открой Postman Web
2. Нажми "Import"
3. Выбери файл `NoRake_Production_API_Import.postman_collection.json`
4. ✅ Готово! Всё настроено автоматически

---

## 📊 Ожидаемые результаты

После успешного прогона:

- ✅ Login вернёт токены
- ✅ Health check покажет `app: ok`, `db: ok`
- ✅ Public endpoints вернут массивы данных
- ✅ Create operations вернут статус 201 + ID
- ✅ Search покажет результаты из всех источников (DB, RAG, MCP)

Все переменные (`workspace_id`, `issue_id`, etc.) автоматически сохранятся для использования в следующих запросах.
