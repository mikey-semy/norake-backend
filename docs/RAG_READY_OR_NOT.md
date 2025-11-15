mikey-semy: rag у нас готов?

GitHub Copilot: Проверю текущее состояние RAG системы в проекте.

Searched codebase for "RAG embeddings chunks document processing vector search semantic search implementation", 14 results

Searched for regex `RAG_CHUNK_SIZE|RAG_CHUNK_OVERLAP|embed|embedding`, 20 results

Searched for files matching `**/document_chunks*.py`, 1 match

Теперь проверю остальные компоненты RAG системы:

Read [](file:///c%3A/Users/Mike/Projects/norake-backend/src/repository/v1/document_chunks.py#1-1), lines 1 to 100

Read [](file:///c%3A/Users/Mike/Projects/norake-backend/src/services/v1/rag_search.py#1-1), lines 1 to 80

Searched for regex `vector_search|_search_rag_context|semantic.*search`, 20 results

Теперь проверю интеграцию с AI чатом:

Read [](file:///c%3A/Users/Mike/Projects/norake-backend/src/services/v1/ai_chat.py#220-220), lines 220 to 280

Read [](file:///c%3A/Users/Mike/Projects/norake-backend/src/services/v1/ai_chat.py#470-470), lines 470 to 540

Searched for regex `RAG_CHUNK_SIZE|RAG_CHUNK_OVERLAP|RAG.*config|Settings.*RAG` (`**/src/core/settings/**`), 2 results

Отлично! Теперь проверю роутеры и финальную интеграцию:

Searched for regex `rag.*search|RAGSearchService|semantic.*search` (`**/src/routers/**`), 3 results

Searched for regex `rag|RAG|embeddings` (`**/src/core/dependencies/**`), 20 results

Read [](file:///c%3A/Users/Mike/Projects/norake-backend/docs/RAG_PHASE2_SUMMARY.md#1-1), lines 1 to 50

Проверю финальные компоненты:

Read [](file:///c%3A/Users/Mike/Projects/norake-backend/src/core/dependencies/search.py#1-1), lines 1 to 100

Read [](file:///c%3A/Users/Mike/Projects/norake-backend/src/core/dependencies/embeddings.py)

Searched for regex `DocumentChunkModel|class.*Chunk|embedding.*Vector` (`**/src/models/v1/**`), 16 results

Проверю окончательный статус Phase 2:

Read [](file:///c%3A/Users/Mike/Projects/norake-backend/docs/RAG_PHASE2_SUMMARY.md#380-380), lines 380 to 468

Read [](file:///c%3A/Users/Mike/Projects/norake-backend/docs/DEVELOPMENT_PLAN.md#1-1), lines 1 to 50

Searched for regex `Phase 3|Phase III|RAG.*Phase.*3|AI.*Chat.*Integration` (`**/docs/**`), 11 results

Теперь составлю подробный план на основе собранной информации:

## Plan: RAG System Status Assessment & Next Steps

Анализ показывает, что RAG система в проекте **практически готова** к использованию. Вот краткий статус и следующие шаги.

### Steps

1. **Проверить завершённость Phase 2 (100% реализовано)** - Все компоненты RAG Phase 2 внедрены и документированы: `langdetect` для определения языка, `progress_percent` для отслеживания прогресса (0→25→50→75→100%), text chunking с алгоритмом sliding window, `OpenRouterEmbeddings` для генерации векторов (1536 dimensions), `DocumentChunkModel` с pgvector для хранения, `RAGSearchService` для семантического поиска через `vector_search()`, интеграция с `AIChatService._search_rag_context()`.

2. **Провести мануальное тестирование по чеклисту** - Следуй `docs/RAG_PHASE2_TESTING.md` (350+ строк гайда): загрузить PDF → активировать `view_pdf` функцию → проверить прогресс обработки (должны видеть 0%→25%→50%→75%→100%) → SQL запросом проверить `document_chunks` таблицу (embeddings 1536 размерности) → опционально протестировать `DocumentChunkRepository.vector_search()` напрямую.

3. **Запустить интеграционное тестирование AI Chat с RAG** - Создать чат с прикреплённым PDF документом → отправить вопрос по содержанию → проверить логи (`RAG поиск для чата %s: найдено %d чанков`) → убедиться что ответ использует контекст из документа (проверить `_format_rag_context()` в промпте).

4. **Оптимизировать производительность при необходимости** - Добавить pgvector индекс (`CREATE INDEX USING ivfflat ... vector_cosine_ops`) для ускорения поиска → измерить латентность semantic search (цель <100ms) → внедрить Redis кеширование для часто запрашиваемых чанков → batch processing для одновременной загрузки нескольких документов.

### Further Considerations

1. **Phase 3 уже интегрирована частично** - `AIChatService` уже использует `RAGSearchService.search()` при наличии `document_service_ids` в чате, контекст добавляется в промпт через `_format_rag_context()`, но отсутствует система цитирования (`chunk_index` → номер страницы). Нужно ли добавить citations сейчас или это можно отложить?

2. **Отсутствие автотестов** - Вся проверка Phase 2 сейчас только мануальная. Рекомендуется написать pytest тесты для: `_chunk_text()` (проверка overlap и sentence boundaries), `vector_search()` (mock pgvector queries), `_process_document_for_rag()` (проверка статусов и progress_percent). Создать тесты?

3. **Мониторинг производительности не настроен** - Для продакшена нужны метрики: время обработки PDF (цель 13-20 сек для 8-страничного), latency embedding generation, vector search response time. Добавить Prometheus metrics или пока обойтись логами?

mikey-semy: Phase 3 уже интегрирована частично - AIChatService уже использует RAGSearchService.search() при наличии document_service_ids в чате, контекст добавляется в промпт через _format_rag_context(), но отсутствует система цитирования (chunk_index → номер страницы). Нужно ли добавить citations сейчас или это можно отложить? ну цитирование было бы полезным, как думаешь, pdf 1000 страниц - это сложно, нам нужны решения облегчить работу нейронке с такими большими файлами

GitHub Copilot: Отличный вопрос! Для работы с большими PDF (1000+ страниц) система цитирования **критична**, но её недостаточно. Нужен комплексный подход.

Read [](file:///c%3A/Users/Mike/Projects/norake-backend/src/models/v1/knowledge_bases.py#338-338), lines 338 to 440

Read [](file:///c%3A/Users/Mike/Projects/norake-backend/src/services/v1/ai_chat.py#510-510), lines 510 to 545

Read [](file:///c%3A/Users/Mike/Projects/norake-backend/src/core/settings/base.py#845-845), lines 845 to 860

Searched for regex `chunk_metadata|page_number|start_page|end_page` (`**/src/services/v1/document_services.py`), 1 result

Searched codebase for "hierarchical chunking recursive splitting page tracking metadata extraction PDF large documents optimization", 13 results

Отлично! Теперь у меня полная картина. Вижу что `PDFProcessor` **уже имеет** `extract_page_text()` и разметка страниц через `--- Page N ---`. Составлю комплексный план оптимизации для больших PDF.

## Plan: Оптимизация RAG для больших PDF (1000+ страниц) + система цитирования

Для работы с большими PDF нужны **три ключевых улучшения**: система цитирования с номерами страниц, hierarchical chunking с сохранением контекста, и умная фильтрация чанков перед отправкой в LLM.

### Steps

1. **Добавить page_number в chunk_metadata при создании чанков** - Модифицировать `DocumentServiceService._chunk_text()` и `_process_document_for_rag()`: извлекать номер страницы из маркеров `--- Page N ---` которые уже добавляет `PDFProcessor._extract_with_pdfplumber()`, сохранять в `chunk_metadata["page_number"]` или `"page_range": [start, end]` для чанков охватывающих несколько страниц, передавать `page_count` параметром в `_chunk_text()` для правильной разбивки.

2. **Реализовать систему цитирования в AIChatService** - Обновить `_format_rag_context()` чтобы включать источник: `**Документ:** {filename}, **Страница:** {page_number}`, добавить в system prompt инструкцию цитировать источники через `[Документ, стр. X]`, создать новый метод `_extract_citations()` для парсинга ответа LLM и валидации ссылок на страницы.

3. **Внедрить hierarchical chunking для сохранения структуры документа** - Создать `HierarchicalChunker` класс в `src/core/integrations/chunking/`: детектировать заголовки через regex/heuristics (CAPS, размер шрифта из PyMuPDF), создавать иерархию чанков (parent chunks = разделы с контекстом, child chunks = параграфы для embedding), сохранять в `chunk_metadata["parent_chunk_id"]` и `"hierarchy_level": 0|1|2`, при RAG search возвращать child chunk + parent context для LLM.

4. **Добавить two-stage RAG retrieval для больших документов** - Первый этап (coarse search): vector search по всему документу с `limit=20`, второй этап (reranking): использовать cross-encoder или LLM для rerank топ-3 самых релевантных, настроить в `settings.RAG_COARSE_LIMIT=20` и `settings.RAG_FINAL_LIMIT=3`, обновить `RAGSearchService.search()` для поддержки двухступенчатого поиска.

5. **Оптимизировать chunking для 1000-страничных PDF** - Увеличить `RAG_CHUNK_SIZE` с 1500 до 2500 символов (уменьшит количество embeddings с ~1500 до ~600 для 1000-стр PDF), добавить батчинг embeddings по 50 чанков (сейчас все сразу → может упасть на timeout), реализовать progressive loading: обрабатывать по 100 страниц за раз с промежуточными checkpoint в `progress_percent`, добавить `PDFProcessor.get_page_ranges(chunk_size=100)` для разбиения на батчи.

### Further Considerations

1. **Adaptive chunking vs фиксированный размер** - Сейчас `RAG_CHUNK_SIZE=1500` для всех документов. Для технической документации (код, таблицы) лучше меньшие чанки (800-1000), для текста (книги, статьи) - большие (2000-3000). Реализовать `ChunkingStrategy` enum (TECHNICAL|TEXT|AUTO) или оставить фиксированный?

2. **Стоимость embeddings для 1000-страничного PDF** - При chunk_size=1500 и average 300 chars/page → ~200 символов/чанк → ~666 чанков → ~$0.08 за документ (ada-002: $0.0001/1K tokens). Для production возможно стоит кешировать embeddings неизменных документов. Добавить проверку `IF extracted_text_hash changed THEN regenerate embeddings`?

3. **Память и производительность pgvector** - Сейчас `ivfflat` индекс хорош до ~100K vectors, для workspace с 1000+ документами (каждый 500+ чанков) может стать медленным. Нужно ли сразу планировать переход на HNSW index (`CREATE INDEX USING hnsw`) который быстрее на больших объёмах но дольше строится? Или оставить ivfflat и мониторить latency?