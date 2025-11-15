# Git Commit Template for RAG Phase 2

## Commit Message

```
feat(rag): Implement Phase 2 - embeddings, chunking, progress tracking

BREAKING CHANGE: Adds progress_percent field to document_processing table

## What's Implemented

### 1. Language Detection (langdetect)
- Auto-detect document language from first 1000 characters
- Replaces hardcoded "ru" with dynamic detection
- Supports 55+ languages (en, ru, es, fr, de, zh-cn, ja, etc.)
- Graceful fallback to "unknown" on error

### 2. Progress Tracking
- New field: document_processing.progress_percent (0-100)
- Real-time updates at each stage:
  * 0% - Processing started
  * 25% - Text extracted + language detected
  * 50% - Text chunked with overlap
  * 75% - Embeddings generated
  * 100% - Vectors stored in database
- Migration: 99067613cd7b_add_progress_percent_to_document_.py

### 3. Text Chunking
- Sliding window algorithm with sentence boundary detection
- Configurable chunk size (RAG_CHUNK_SIZE=1500 chars)
- Configurable overlap (RAG_CHUNK_OVERLAP=200 chars)
- Preserves sentence integrity (no mid-sentence splits)

### 4. Embeddings Generation
- Integration with OpenRouterEmbeddings via dependency injection
- Model: openai/text-embedding-ada-002 (1536 dimensions)
- Retry logic with exponential backoff
- Batch processing for efficiency

### 5. Vector Storage
- Store chunks with embeddings in DocumentChunkModel
- pgvector support for semantic similarity search
- Bulk insert for performance (single transaction)
- Rich metadata (language, chunk_size, overlap, extraction_method)

## Files Changed

### Modified (6 files)
- pyproject.toml: Add langdetect>=1.0.9 dependency
- src/models/v1/document_processing.py: Add progress_percent field
- src/services/v1/document_services.py: Extend RAG processing pipeline
  * Add _chunk_text() method (62 lines)
  * Update _process_document_for_rag() with Phase 2 steps (125 lines)
  * Add imports: langdetect, os, tempfile, DocumentChunkRepository
  * Update __init__() to accept embeddings parameter
- src/core/dependencies/__init__.py: Export EmbeddingsDep
- src/core/dependencies/document_services.py: Inject EmbeddingsDep
- uv.lock: Update dependencies lockfile

### New Files (5 files)
- src/core/dependencies/embeddings.py: Embeddings dependency provider
- src/core/migrations/versions/99067613cd7b_*.py: progress_percent migration
- docs/RAG_AUTO_PROCESSING.md: Updated RAG documentation with Phase 2
- docs/RAG_PHASE2_TESTING.md: Comprehensive testing guide (350+ lines)
- docs/RAG_PHASE2_SUMMARY.md: Implementation summary and sign-off

## Testing

Manual testing required (see docs/RAG_PHASE2_TESTING.md):
1. Upload PDF document
2. Activate view_pdf function
3. Monitor progress: 0% → 25% → 50% → 75% → 100%
4. Verify language auto-detected (not "ru")
5. Verify chunks stored with embeddings (1536 dimensions)
6. Test semantic search via DocumentChunkRepository.vector_search()

## Performance

Expected processing time (8-page PDF, ~20KB text): 13-20 seconds
- Text extraction: 3-5s (0% → 25%)
- Language detection: <0.1s
- Chunking: 0.5-1s (25% → 50%)
- Embeddings: 8-12s (50% → 75%)
- Vector storage: 1-2s (75% → 100%)

## Migration

Run before deployment:
```bash
uv run alembic upgrade head
```

Applied migration: 99067613cd7b (adds progress_percent column)

## Related Issues

Closes: NORAK-XX (replace with actual Plane issue ID)

## Documentation

- RAG_AUTO_PROCESSING.md: Updated with Phase 2 details
- RAG_PHASE2_TESTING.md: Complete testing workflow
- RAG_PHASE2_SUMMARY.md: Implementation summary
```

## Git Commands

```bash
# Stage all changes
git add .

# Commit with message from above
git commit -F .git/COMMIT_TEMPLATE.txt

# Or commit interactively:
git commit

# Push to development branch
git push origin development
```

## Pre-commit Checklist

- [x] All 7 TODO tasks completed
- [x] Migration applied: `uv run alembic upgrade head`
- [x] No linting errors: get_errors() shows clean
- [x] langdetect dependency installed and working
- [x] Documentation updated (3 docs files)
- [x] Testing guide created
- [x] All files tracked by git (use `git status`)
- [ ] Manual testing completed (follow RAG_PHASE2_TESTING.md)
- [ ] Code review requested from backend team
- [ ] Plane issue updated (mark as "Done" with summary comment)

## Post-commit Actions

1. **Update Plane Issue**:
   - Status: "Done" (state_id: 749a5e1b-a62a-4b50-964b-816ffe1f4dad)
   - Comment: "RAG Phase 2 implemented: language detection, chunking, embeddings, progress tracking, vector storage. See commit <hash> for details."

2. **Notify Team**:
   - Share testing guide (RAG_PHASE2_TESTING.md)
   - Request code review on development branch
   - Coordinate manual testing session

3. **Plan Phase 3**:
   - AI Chat integration (use DocumentChunkRepository for RAG)
   - Frontend progress bar component
   - Performance optimization (pgvector index)
