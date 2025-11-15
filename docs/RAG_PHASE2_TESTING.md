# RAG Phase 2 Testing Guide

## ✅ Implementation Status

**All Phase 2 components implemented:**
1. ✅ Language detection (langdetect)
2. ✅ Text chunking (sliding window + sentence boundaries)
3. ✅ Embeddings generation (OpenRouter API)
4. ✅ Progress tracking (0% → 25% → 50% → 75% → 100%)
5. ✅ Vector storage (DocumentChunkModel with pgvector)

## 🧪 Testing Workflow

### 1. Prerequisites

**Environment variables** (.env.dev):
```bash
# OpenRouter API (required for embeddings)
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_EMBEDDING_MODEL=openai/text-embedding-ada-002

# PostgreSQL with pgvector
POSTGRES_DB=norake_dev
POSTGRES_USER=norake_user
POSTGRES_PASSWORD=norake_password

# S3 Storage
S3_BUCKET_NAME=norake-documents-dev
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

**Database migration**:
```bash
# Apply progress_percent migration
uv run alembic upgrade head

# Verify column added
# psql: SELECT column_name FROM information_schema.columns WHERE table_name='document_processing';
# Should include: progress_percent
```

### 2. Upload Test Document

**Request**:
```bash
POST /api/v1/document-services
Content-Type: multipart/form-data

{
  "workspace_id": "uuid-of-workspace",
  "name": "Test RAG Document",
  "category": "design",
  "file": (PDF file, 5-10 pages)
}
```

**Expected response**:
```json
{
  "success": true,
  "message": "Document service created",
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Test RAG Document",
    "file_url": "https://s3.../documents/test.pdf",
    "available_functions": [
      {"name": "qr_code", "enabled": false, "price": 0},
      {"name": "view_pdf", "enabled": false, "price": 0}
    ]
  }
}
```

### 3. Activate view_pdf (Triggers RAG Processing)

**Request**:
```bash
POST /api/v1/document-services/{document_id}/functions
Content-Type: application/json

{
  "name": "view_pdf",
  "enabled": true
}
```

**Expected response** (immediate, non-blocking):
```json
{
  "success": true,
  "message": "Function view_pdf activated",
  "data": {
    "available_functions": [
      {"name": "view_pdf", "enabled": true, "price": 0}
    ],
    "processing": {
      "id": "proc-uuid-...",
      "status": "PENDING",
      "progress_percent": 0,
      "created_at": "2024-01-15T10:00:00Z"
    }
  }
}
```

**Backend logs** (check console):
```
INFO - Активирована функция view_pdf для <document_id>, запуск RAG обработки...
INFO - Начата RAG обработка документа <document_id> (processing_id=<proc_id>)
```

### 4. Monitor Progress

**Request** (poll every 2-5 seconds):
```bash
GET /api/v1/document-services/{document_id}/functions
```

**Expected progression**:

**Stage 1: Text Extraction (0% → 25%)**
```json
{
  "processing": {
    "status": "PROCESSING",
    "progress_percent": 0,
    "extracted_text": null
  }
}

// 3-5 seconds later:
{
  "processing": {
    "status": "PROCESSING",
    "progress_percent": 25,
    "extracted_text": "Document text here...",
    "page_count": 8,
    "language": "en"  // ✅ Auto-detected!
  }
}
```

**Stage 2: Chunking (25% → 50%)**
```json
{
  "processing": {
    "status": "PROCESSING",
    "progress_percent": 50
  }
}
```

**Backend logs**:
```
INFO - Документ <doc_id> разбит на 12 чанков (размер=1500, overlap=200)
```

**Stage 3: Embeddings Generation (50% → 75%)**
```json
{
  "processing": {
    "status": "PROCESSING",
    "progress_percent": 75
  }
}
```

**Backend logs**:
```
INFO - Генерируем embeddings для 12 чанков...
INFO - Сгенерировано 12 embeddings для документа <doc_id>
```

**Stage 4: Vector Storage (75% → 100%)**
```json
{
  "processing": {
    "status": "PROCESSING",
    "progress_percent": 100
  }
}

// Final state:
{
  "processing": {
    "status": "COMPLETED",
    "progress_percent": 100,
    "processing_time_seconds": 15,
    "extracted_text": "Full document text...",
    "page_count": 8,
    "language": "en"
  }
}
```

**Backend logs**:
```
INFO - Сохранено 12 чанков с embeddings для документа <doc_id>
INFO - RAG обработка документа <doc_id> завершена успешно за 15.23 сек: 8 страниц, 12 чанков, 12 embeddings
```

### 5. Verify Vector Storage

**Database query** (PostgreSQL):
```sql
-- Check chunks table
SELECT 
    dc.id,
    dc.document_id,
    dc.chunk_index,
    LENGTH(dc.content) as content_length,
    array_length(dc.embedding, 1) as embedding_dimensions,
    dc.token_count,
    dc.chunk_metadata
FROM document_chunks dc
WHERE dc.document_id = '<document_id>'
ORDER BY dc.chunk_index;

-- Expected output:
-- chunk_index | content_length | embedding_dimensions | token_count | chunk_metadata
-- 0           | 1500           | 1536                 | 250         | {"language": "en", "chunk_size": 1500, ...}
-- 1           | 1500           | 1536                 | 248         | {"language": "en", "chunk_size": 1500, ...}
-- ...
-- 11          | 800            | 1536                 | 120         | {"language": "en", "chunk_size": 800, ...}
```

### 6. Test Semantic Search (Optional)

**Python console** (test vector search):
```python
import asyncio
from src.repository.v1.document_chunks import DocumentChunkRepository
from src.core.integrations.ai.embeddings.openrouter import OpenRouterEmbeddings
from src.core.database import get_async_session

async def test_search():
    async for session in get_async_session():
        # Generate query embedding
        embeddings = OpenRouterEmbeddings()
        query = "What is the main topic of this document?"
        query_embedding = await embeddings.embed_query(query)
        
        # Search similar chunks
        chunk_repo = DocumentChunkRepository(session)
        results = await chunk_repo.vector_search(
            embedding=query_embedding,
            kb_id=document_id,  # Your document ID
            limit=3,
            min_similarity=0.7
        )
        
        for idx, chunk in enumerate(results):
            print(f"\n--- Chunk {idx+1} (index {chunk.chunk_index}) ---")
            print(f"Content: {chunk.content[:200]}...")
            print(f"Tokens: {chunk.token_count}")
        
        await embeddings.close()
        break

asyncio.run(test_search())
```

**Expected output**:
```
--- Chunk 1 (index 0) ---
Content: This document provides an overview of the system architecture, focusing on the main components...
Tokens: 250

--- Chunk 2 (index 3) ---
Content: The main topic discussed in this section is the integration of various modules...
Tokens: 248

--- Chunk 3 (index 7) ---
Content: Key architectural decisions are documented here, including the choice of technologies...
Tokens: 235
```

## 🐛 Troubleshooting

### Issue: "progress_percent" column doesn't exist

**Solution**: Run migration
```bash
uv run alembic upgrade head
```

### Issue: Language always "unknown"

**Check**:
1. Document has actual text (not scanned image PDF)
2. langdetect installed: `uv pip list | grep langdetect`
3. Backend logs: Check for LangDetectException

**Fix**:
```bash
uv add langdetect>=1.0.9
```

### Issue: Embeddings generation fails

**Check**:
1. OPENROUTER_API_KEY in .env.dev
2. API key valid: `curl -H "Authorization: Bearer $OPENROUTER_API_KEY" https://openrouter.ai/api/v1/models`
3. Backend logs: Check for rate limit errors

**Fix**:
- Verify API key has credits
- Check OpenRouter dashboard for quota

### Issue: Chunks not saved in database

**Check**:
1. pgvector extension installed: `psql -c "SELECT * FROM pg_extension WHERE extname='vector';"`
2. DocumentChunkModel table exists: `psql -c "\d document_chunks;"`
3. Backend logs: Check for bulk_create errors

**Fix** (if pgvector missing):
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Issue: Processing stuck at PROCESSING

**Check**:
1. Backend logs for exceptions
2. Processing record: `SELECT * FROM document_processing WHERE id='<proc_id>';`
3. Task still running: Check for "RAG обработка документа ... завершена" log

**Manual fix**:
```sql
UPDATE document_processing 
SET status = 'FAILED', 
    error_message = 'Manual intervention - timeout'
WHERE id = '<proc_id>';
```

## 📊 Performance Benchmarks

**Expected timings** (8-page PDF, ~20KB text):

| Stage                | Time    | Progress |
|----------------------|---------|----------|
| Text extraction      | 3-5s    | 0% → 25% |
| Language detection   | <0.1s   | 25%      |
| Chunking             | 0.5-1s  | 25% → 50%|
| Embeddings (12 chunks)| 8-12s  | 50% → 75%|
| Vector storage       | 1-2s    | 75% → 100%|
| **Total**            | **13-20s**| **100%** |

**Factors affecting performance**:
- PDF size (pages, file size)
- Text density (tokens per page)
- Number of chunks (text length / chunk_size)
- OpenRouter API latency (embedding generation)
- PostgreSQL performance (bulk insert)

## ✅ Success Criteria Checklist

- [ ] PDF uploaded successfully to S3
- [ ] view_pdf activation returns HTTP 200 immediately (non-blocking)
- [ ] DocumentProcessingModel created with PENDING status
- [ ] Progress updates: 0% → 25% → 50% → 75% → 100%
- [ ] Language auto-detected (not hardcoded "ru")
- [ ] Extracted text saved in document_processing.extracted_text
- [ ] Chunks created with overlap (check logs for count)
- [ ] Embeddings generated (1536 dimensions each)
- [ ] Chunks stored in document_chunks table with vectors
- [ ] Final status: COMPLETED
- [ ] processing_time_seconds populated
- [ ] Semantic search returns relevant chunks (optional test)
- [ ] No errors in backend logs

## 🚀 Next Steps

After successful Phase 2 testing:

1. **Integrate with AI Chat** (Phase 3):
   - Modify ai_chat.py to use DocumentChunkRepository.vector_search()
   - Add RAG context to system prompt
   - Implement citation system (chunk_index → page number)

2. **Optimize Performance**:
   - Add pgvector HNSW/IVFFlat index for faster search
   - Implement batch embedding with retry logic
   - Add Redis caching for frequently searched chunks

3. **Enhance Frontend**:
   - Real-time progress bar during processing
   - Display chunk count and embedding status
   - Show estimated time remaining

4. **Production Readiness**:
   - Add monitoring (Prometheus metrics for processing times)
   - Implement cleanup job (delete orphaned chunks)
   - Add admin endpoint to re-process failed documents
