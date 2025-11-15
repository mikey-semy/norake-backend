# Автоматическая RAG Обработка Документов

## 🎯 Обзор

При активации функции `view_pdf` для DocumentService автоматически запускается фоновая обработка документа для подготовки RAG данных. Обработка происходит асинхронно и не блокирует HTTP ответ пользователю.

**Фазы реализации**:
- ✅ **Phase 1 (COMPLETED)**: Text extraction - автоизвлечение текста из PDF
- ✅ **Phase 2 (COMPLETED)**: Embeddings + Vector storage - chunking, генерация embeddings, сохранение в векторную БД с прогресс-баром

## 🔄 Workflow

```
Пользователь активирует view_pdf
         ↓
POST /document-services/{id}/functions
  {"name": "view_pdf", "enabled": true}
         ↓
add_function() обнаруживает активацию
         ↓
Проверка DocumentProcessingModel
         ↓
   Если уже COMPLETED → пропускаем
   Если нет → создаём запись (PENDING)
         ↓
asyncio.create_task() запускает _process_document_for_rag()
         ↓
HTTP 200 возвращается пользователю (мгновенно!)
         ↓
=== ФОНОВАЯ ОБРАБОТКА (Phase 1 + Phase 2) ===
         ↓
0. Статус → PROCESSING, progress_percent: 0%
1. Скачивание PDF из S3
2. Создание временного файла
3. Извлечение текста (PDFProcessor)
4. Подсчёт страниц
5. progress_percent: 25% → Автоопределение языка (langdetect)
6. progress_percent: 50% → Chunking текста (sliding window + overlap)
7. progress_percent: 75% → Генерация embeddings (OpenRouter API)
8. progress_percent: 100% → Сохранение chunks + vectors в DocumentChunkModel (pgvector)
9. Статус → COMPLETED
         ↓
Документ готов для AI чата с RAG + семантический поиск
```

## 📦 Компоненты

### Phase 2 Implementation Details

#### 1. **Language Detection** (Автоопределение языка)

**Библиотека**: `langdetect>=1.0.9`

**Реализация** (document_services.py):
```python
from langdetect import detect, LangDetectException

# В _process_document_for_rag():
try:
    language = detect(extracted_text[:1000]) if extracted_text else "unknown"
except LangDetectException:
    language = "unknown"
    self.logger.warning("Не удалось определить язык для документа %s", service_id)

# Сохранение с определённым языком
await self.processing_repo.save_extracted_text(
    processing_id=processing_id,
    extracted_text=extracted_text,
    language=language,  # ✅ Автоопределение вместо "ru"
)
```

**Особенности**:
- Анализ первых 1000 символов текста
- Fallback на "unknown" при ошибке
- Поддержка 55+ языков (en, ru, es, fr, de, zh-cn, ja и т.д.)

#### 2. **Text Chunking** (Разбиение на чанки)

**Алгоритм**: Sliding window с определением границ предложений

**Реализация** (document_services.py, метод `_chunk_text()`):
```python
def _chunk_text(self, text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """
    Разбиение текста на чанки с перекрытием для RAG.

    Args:
        text: Исходный текст для разбиения.
        chunk_size: Размер чанка в символах (default: 1500).
        chunk_overlap: Перекрытие между чанками в символах (default: 200).

    Returns:
        Список чанков текста.
    """
    # Sliding window algorithm with sentence boundary detection
    # См. document_services.py:1338-1410 для полной реализации
```

**Настройки** (src/core/settings/base.py):
```python
RAG_CHUNK_SIZE: int = 1500        # Размер чанка в символах
RAG_CHUNK_OVERLAP: int = 200      # Перекрытие между чанками
```

**Особенности**:
- ✅ Учёт границ предложений (не разрывает предложения)
- ✅ Перекрытие для контекста (200 символов по умолчанию)
- ✅ Обработка документов любого размера
- ✅ Кэширование разделителей предложений

#### 3. **Embeddings Generation** (Генерация векторов)

**Клиент**: `OpenRouterEmbeddings` (src/core/integrations/ai/embeddings/openrouter.py)

**Модель**: `openai/text-embedding-ada-002` (1536 dimensions)

**Реализация** (document_services.py):
```python
# Dependency injection в __init__():
def __init__(self, session, s3_client, settings, embeddings, workspace_service=None):
    self.embeddings = embeddings  # OpenRouterEmbeddings instance

# В _process_document_for_rag():
chunks = self._chunk_text(
    text=extracted_text,
    chunk_size=self.settings.RAG_CHUNK_SIZE,
    chunk_overlap=self.settings.RAG_CHUNK_OVERLAP,
)

embeddings_list = await self.embeddings.embed(chunks)
self.logger.info(
    "Сгенерировано %d embeddings для документа %s",
    len(embeddings_list),
    service_id,
)
```

**Настройки** (src/core/settings/base.py):
```python
OPENROUTER_EMBEDDING_MODEL: str = "openai/text-embedding-ada-002"
OPENROUTER_API_URL: str = "https://openrouter.ai/api/v1"
```

**Особенности**:
- ✅ Retry logic с exponential backoff
- ✅ Rate limiting
- ✅ Batch processing (оптимизация по токенам)
- ✅ Полное логирование ошибок

#### 4. **Progress Tracking** (Отслеживание прогресса)

**Модель** (src/models/v1/document_processing.py):
```python
progress_percent: Mapped[int] = mapped_column(
    Integer, nullable=False, default=0, server_default="0",
    doc="Процент выполнения обработки (0-100)",
)
```

**Миграция**: `99067613cd7b_add_progress_percent_to_document_.py`

**Workflow прогресса**:
```python
# В _process_document_for_rag():
await self.processing_repo.update_item(processing_id, {"progress_percent": 0})    # Start
await self.processing_repo.update_item(processing_id, {"progress_percent": 25})   # Text extracted
await self.processing_repo.update_item(processing_id, {"progress_percent": 50})   # Chunks created
await self.processing_repo.update_item(processing_id, {"progress_percent": 75})   # Embeddings generated
await self.processing_repo.update_item(processing_id, {"progress_percent": 100})  # Completed
```

**Frontend интеграция**:
```javascript
// Poll processing status
const response = await fetch(`/api/v1/document-services/${id}/functions`);
const processing = response.data.processing;

// Show progress bar
<ProgressBar value={processing.progress_percent} max={100} />
// "Обработка: 75% - генерация embeddings..."
```

#### 5. **Vector Storage** (Сохранение в векторную БД)

**Модель** (src/models/v1/knowledge_bases.py):
```python
class DocumentChunkModel(BaseModel):
    __tablename__ = "document_chunks"

    document_id: Mapped[UUID] = mapped_column(ForeignKey("document_services.id"))
    chunk_index: Mapped[int]
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[Vector] = mapped_column(Vector(1536))  # pgvector!
    token_count: Mapped[int]
    chunk_metadata: Mapped[dict] = mapped_column(JSONB)
```

**Repository** (src/repository/v1/document_chunks.py):
```python
class DocumentChunkRepository(BaseRepository[DocumentChunkModel]):
    async def bulk_create(self, chunk_data: list[dict]) -> list[DocumentChunkModel]:
        # Bulk insert для производительности

    async def vector_search(
        self,
        embedding: list[float],
        kb_id: UUID,
        limit: int = 5,
        min_similarity: float = 0.7
    ) -> list[DocumentChunkModel]:
        # Cosine similarity search via pgvector
```

**Реализация** (document_services.py):
```python
# В _process_document_for_rag():
chunk_repo = DocumentChunkRepository(self.repository.session)
chunk_data = [
    {
        "document_id": service.id,
        "chunk_index": idx,
        "content": chunk,
        "embedding": embedding,
        "token_count": len(chunk.split()),  # Грубая оценка
        "chunk_metadata": {
            "chunk_size": len(chunk),
            "chunk_overlap": self.settings.RAG_CHUNK_OVERLAP,
            "language": language,
            "extraction_method": ExtractionMethod.PDFPLUMBER.value,
        },
    }
    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings_list))
]
await chunk_repo.bulk_create(chunk_data)
```

**pgvector индекс** (для производительности):
```sql
-- В миграции (опционально, но рекомендуется):
CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops);
```

### 1. Системный Промпт (Settings)

**Файл**: `src/core/settings/base.py`

```python
AI_CHAT_DEFAULT_SYSTEM_PROMPT: str = """Ты - полезный AI ассистент для работы с документами и решения проблем.

Правила работы:
1. Отвечай на русском языке, используй markdown для форматирования
2. Если есть документы в контексте (RAG) - используй их для точных ответов
3. При цитировании документов указывай источник
4. Если не уверен в ответе - честно скажи об этом
5. Для технических вопросов давай конкретные примеры кода

Стиль общения: профессиональный, дружелюбный, конструктивный."""
```

**Использование**:
```python
from src.core.settings.base import settings

# В ai_chat.py при создании чата:
system_prompt = request.system_prompt or settings.AI_CHAT_DEFAULT_SYSTEM_PROMPT
```

### 2. Триггер Автообработки (DocumentServiceService)

**Файл**: `src/services/v1/document_services.py`

**Метод**: `add_function()` (строки ~565-625)

```python
# После добавления функции в JSONB
if function.name == "view_pdf" and function.enabled:
    self.logger.info(
        "Активирована функция view_pdf для %s, запуск RAG обработки...",
        service_id,
    )
    try:
        # Проверить существующую обработку
        processing = await self.processing_repo.get_by_document_id(service_id)

        if not processing:
            # Создать запись о начале обработки
            processing = await self.processing_repo.create_processing_record(
                document_service_id=service_id,
                status=ProcessingStatus.PENDING,
            )

        # Если обработка уже завершена - не запускать заново
        if processing.status == ProcessingStatus.COMPLETED:
            self.logger.info("Документ %s уже обработан, пропускаем", service_id)
        else:
            # Запустить обработку асинхронно (не блокируем ответ)
            asyncio.create_task(
                self._process_document_for_rag(service_id, processing.id)
            )
    except Exception as e:
        self.logger.error("Ошибка при запуске RAG обработки: %s", str(e))
        # Не прерываем добавление функции
```

**Ключевые особенности**:
- ✅ **Идемпотентность**: Проверяет статус COMPLETED, пропускает повторную обработку
- ✅ **Неблокирующий**: `asyncio.create_task()` - HTTP ответ мгновенный
- ✅ **Отказоустойчивость**: Ошибки не прерывают добавление функции
- ✅ **Логирование**: Детальные логи на всех этапах

### 3. Фоновая Обработка (DocumentServiceService)

**Файл**: `src/services/v1/document_services.py`

**Метод**: `_process_document_for_rag()` (строки ~1345-1458)

```python
async def _process_document_for_rag(
    self,
    service_id: UUID,
    processing_id: UUID,
) -> None:
    """
    Фоновая обработка документа для RAG (извлечение текста + эмбеддинги).

    Workflow:
        1. Обновить статус → PROCESSING
        2. Скачать файл из S3
        3. Извлечь текст (PDFProcessor)
        4. Создать эмбеддинги (chunks) ⏳ TODO
        5. Сохранить в DocumentProcessingModel
        6. Обновить статус → COMPLETED
    """
    start_time = time.time()

    try:
        # 1. Update status to PROCESSING
        await self.processing_repo.update_status(processing_id, ProcessingStatus.PROCESSING)

        # 2. Get document from DB
        service = await self.repository.get_item_by_id(service_id)

        # 3. Download file from S3
        file_key = service.file_url.split("/")[-1]
        file_content, content_type = await self.storage.get_file_stream(file_key)

        # 4. Extract text via PDFProcessor
        pdf_processor = PDFProcessor()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            extracted_text = await pdf_processor.extract_text(tmp_path)
            page_count = await pdf_processor.get_page_count(tmp_path)
        finally:
            os.unlink(tmp_path)  # Обязательная очистка

        # 5. Save extracted text to DB
        await self.processing_repo.save_extracted_text(
            processing_id=processing_id,
            extracted_text=extracted_text,
            page_count=page_count,
            extraction_method=ExtractionMethod.PDFPLUMBER,
            language="ru",  # TODO: Auto-detect language
        )

        # 6. Update status to COMPLETED
        processing_time = time.time() - start_time
        await self.processing_repo.update_item(
            processing_id,
            {"status": ProcessingStatus.COMPLETED, "processing_time_seconds": int(processing_time)}
        )

        self.logger.info(
            "✅ RAG обработка завершена для %s за %d сек",
            service_id,
            int(processing_time),
        )

    except Exception as e:
        self.logger.error("Ошибка при RAG обработке: %s", str(e), exc_info=True)
        await self.processing_repo.update_status(
            processing_id,
            ProcessingStatus.FAILED,
            error_message=str(e)[:500]
        )
```

**Ключевые особенности**:
- ✅ **Статусы**: PENDING → PROCESSING → COMPLETED/FAILED
- ✅ **Temp файлы**: Безопасная работа с временными файлами (try/finally cleanup)
- ✅ **Производительность**: Отслеживание `processing_time_seconds`
- ✅ **Ошибки**: Все исключения ловятся, статус → FAILED с сообщением об ошибке
- ⏳ **TODO**: Генерация эмбеддингов (chunking + векторизация)

### 4. Модель Обработки (DocumentProcessingModel)

**Файл**: `src/models/v1/document_processing.py`

**Enum: ProcessingStatus**
```python
class ProcessingStatus(str, Enum):
    """Статусы обработки документа для RAG."""
    PENDING = "pending"       # Ожидает обработки
    PROCESSING = "processing" # Обрабатывается
    COMPLETED = "completed"   # Обработка завершена
    FAILED = "failed"         # Ошибка обработки
```

**Enum: ExtractionMethod**
```python
class ExtractionMethod(str, Enum):
    """Методы извлечения текста из PDF."""
    PDFPLUMBER = "pdfplumber"
    PYMUPDF = "pymupdf"
    OCR = "ocr"
```

**Модель: DocumentProcessingModel**
```python
class DocumentProcessingModel(BaseModel):
    """
    Модель для хранения информации об обработке документа для RAG.

    Связь: 1-to-1 с DocumentServiceModel
    """
    document_service_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_services.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus),
        default=ProcessingStatus.PENDING,
        nullable=False,
    )

    extraction_method: Mapped[ExtractionMethod | None] = mapped_column(
        Enum(ExtractionMethod),
        nullable=True,
    )

    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    processing_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationship
    document_service: Mapped["DocumentServiceModel"] = relationship(
        back_populates="processing",
        lazy="selectin",
    )
```

## 🔧 Настройки (Settings)

**Файл**: `src/core/settings/base.py`

```python
# RAG Configuration (уже существующие настройки)
RAG_CHUNK_SIZE: int = 1500         # Размер chunk для эмбеддингов
RAG_CHUNK_OVERLAP: int = 200       # Overlap между chunks
OPENROUTER_EMBEDDING_MODEL: str = "openai/text-embedding-ada-002"

# AI Chat Configuration (новая настройка)
AI_CHAT_DEFAULT_SYSTEM_PROMPT: str = """..."""
```

## 📊 API Endpoints

### Добавление Функции (Активация RAG)

**POST** `/api/v1/document-services/{service_id}/functions`

**Request Body**:
```json
{
  "name": "view_pdf",
  "enabled": true
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Функция 'view_pdf' успешно добавлена",
  "data": {
    "id": "uuid",
    "title": "Техническая документация",
    "available_functions": [
      {
        "name": "view_pdf",
        "enabled": true,
        "metadata": {}
      }
    ],
    // ... другие поля
  }
}
```

**Что происходит**:
1. HTTP 200 возвращается сразу
2. В фоне запускается `_process_document_for_rag()`
3. Статус обработки можно отслеживать через `GET /document-services/{id}/functions`

### Проверка Статуса Обработки

**GET** `/api/v1/document-services/{service_id}/functions`

**Response** (200 OK):
```json
{
  "success": true,
  "message": "AI функции получены",
  "data": [
    {
      "name": "smart_search",
      "display_name": "Умный поиск",
      "description": "Семантический поиск...",
      "status": "ready"  // или "processing", "inactive", "failed"
    },
    {
      "name": "view_pdf",
      "display_name": "Просмотр PDF",
      "description": "Базовая функция...",
      "status": "processing"  // ← Обработка в процессе
    }
    // ...
  ]
}
```

**Возможные статусы**:
- `"inactive"` - функция не активирована
- `"processing"` - обработка в процессе
- `"ready"` - готов к использованию
- `"failed"` - ошибка при обработке

## 🎯 Workflow для Frontend

```typescript
// 1. Пользователь активирует view_pdf
const response = await fetch(`/api/v1/document-services/${docId}/functions`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    name: 'view_pdf',
    enabled: true,
  }),
});

// 2. Функция добавлена, обработка началась в фоне
if (response.ok) {
  console.log('✅ Функция активирована, обработка началась');

  // 3. Опционально: поллинг статуса
  const checkStatus = async () => {
    const functionsResponse = await fetch(
      `/api/v1/document-services/${docId}/functions`
    );
    const data = await functionsResponse.json();

    const viewPdf = data.data.find((f: any) => f.name === 'view_pdf');

    if (viewPdf.status === 'ready') {
      console.log('✅ Документ готов для AI чата');
      enableChatWithDocument(docId);
    } else if (viewPdf.status === 'processing') {
      console.log('⏳ Обработка в процессе...');
      setTimeout(checkStatus, 5000); // Повторить через 5 сек
    } else if (viewPdf.status === 'failed') {
      console.error('❌ Ошибка при обработке документа');
      showErrorNotification();
    }
  };

  checkStatus();
}
```

## ✅ Реализовано

- [x] Настройка системного промпта (AI_CHAT_DEFAULT_SYSTEM_PROMPT)
- [x] Автоматическая активация обработки при `view_pdf` + `enabled=true`
- [x] Фоновая обработка (asyncio.create_task)
- [x] Скачивание PDF из S3
- [x] Извлечение текста через PDFProcessor
- [x] Безопасная работа с временными файлами
- [x] Отслеживание статусов (PENDING → PROCESSING → COMPLETED/FAILED)
- [x] Логирование всех этапов
- [x] Сохранение extracted_text в DocumentProcessingModel
- [x] Подсчёт времени обработки (processing_time_seconds)
- [x] Обработка ошибок с сохранением error_message
- [x] Идемпотентность (пропуск повторной обработки)

## ⏳ Pending (TODO)

### 1. Генерация Эмбеддингов

```python
# Добавить в _process_document_for_rag() после извлечения текста:

# 7. Chunk text
from src.core.integrations.chunking import TextChunker
chunker = TextChunker(
    chunk_size=settings.RAG_CHUNK_SIZE,      # 1500
    chunk_overlap=settings.RAG_CHUNK_OVERLAP, # 200
)
chunks = chunker.split_text(extracted_text)

# 8. Generate embeddings
from src.core.integrations.openrouter import OpenRouterClient
embeddings = await openrouter_client.create_embeddings(
    texts=chunks,
    model=settings.OPENROUTER_EMBEDDING_MODEL,
)

# 9. Store in vector database
from src.repository.v1.embeddings import EmbeddingsRepository
await embeddings_repo.store_batch(
    document_service_id=service_id,
    chunks=chunks,
    embeddings=embeddings,
)
```

### 2. Автоопределение Языка

```python
from langdetect import detect

# В _process_document_for_rag() после извлечения текста:
detected_language = detect(extracted_text[:1000])  # Первые 1000 символов

await self.processing_repo.save_extracted_text(
    ...
    language=detected_language,  # Вместо "ru"
)
```

### 3. Прогресс-бар для Frontend

**Добавить поле в DocumentProcessingModel**:
```python
progress_percent: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True)
```

**Обновлять на каждом этапе**:
```python
# После скачивания S3
await self.processing_repo.update_item(processing_id, {"progress_percent": 25})

# После извлечения текста
await self.processing_repo.update_item(processing_id, {"progress_percent": 50})

# После chunking
await self.processing_repo.update_item(processing_id, {"progress_percent": 75})

# После embeddings
await self.processing_repo.update_item(processing_id, {"progress_percent": 100})
```

### 4. Уведомления

Отправлять уведомление пользователю при завершении обработки (через WebSocket или email).

### 5. Переобработка При Изменении Документа

При обновлении файла документа сбрасывать статус на PENDING и запускать переобработку.

## 🐛 Отладка

### Логи

```bash
# Просмотр логов обработки
tail -f logs/app.log | grep "RAG обработка"

# Фильтр по document_service_id
tail -f logs/app.log | grep "faa82a60-..."
```

### Проверка Статуса в БД

```sql
SELECT
    ds.id,
    ds.title,
    dp.status,
    dp.processing_time_seconds,
    dp.error_message,
    dp.created_at
FROM document_services ds
LEFT JOIN document_processing dp ON dp.document_service_id = ds.id
WHERE ds.id = 'uuid-here';
```

### Ручной Запуск Обработки

```python
from src.services.v1.document_services import DocumentServiceService
from src.core.dependencies import get_async_session

async with get_async_session() as session:
    service = DocumentServiceService(session=session)
    await service._process_document_for_rag(
        service_id=UUID("..."),
        processing_id=UUID("...")
    )
```

## 📚 Связанные Документы

- **FRONTEND_CHAT_INTEGRATION.md** - интеграция плавающего чата с документами
- **DOCUMENT_SERVICES_QUICK_START.md** - быстрый старт с document services
- **FIXTURES_GUIDE.md** - работа с фикстурами (включая DocumentProcessingModel)

## 🔗 Архитектура RAG

```
DocumentServiceModel (1)
        ↓
        ↓ 1-to-1 relationship
        ↓
DocumentProcessingModel (1)
        ↓
        ↓ extracted_text (Text field)
        ↓
    [Pending: Embeddings]
        ↓
        ↓ 1-to-many (future)
        ↓
  EmbeddingsModel (many)
        ↓
        ↓ vector field
        ↓
   Vector Database Search
```

## 🎉 Итоги

Реализована автоматическая фоновая обработка документов при активации `view_pdf` функции:

1. ✅ **Мгновенный HTTP ответ** - пользователь не ждёт
2. ✅ **Асинхронная обработка** - всё происходит в фоне
3. ✅ **Отслеживание статусов** - frontend может показывать прогресс
4. ✅ **Идемпотентность** - не обрабатывает повторно
5. ✅ **Отказоустойчивость** - ошибки не ломают систему
6. ⏳ **Ожидает эмбеддингов** - текст извлечён, векторизация pending

**Следующий шаг**: Реализация генерации эмбеддингов и векторного поиска для полноценного RAG.
