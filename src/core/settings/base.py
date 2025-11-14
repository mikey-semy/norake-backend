"""
Модуль base.py — базовые настройки приложения.

Содержит основной класс Settings, который агрегирует все параметры конфигурации микросервиса:
- Логирование (logging)
- Пути и окружение (paths)
- Настройки баз данных (database)
- Кэш (cache)
- Параметры FastAPI и Uvicorn
- CORS

Экспортируемые объекты:
- Settings: Главный класс настроек приложения (через pydantic).
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, ClassVar, Optional

from pydantic import PostgresDsn, RedisDsn, AmqpDsn, SecretStr, EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.lifespan import lifespan

logger = logging.getLogger(__name__)


class PathSettings(BaseSettings):
    """
    Класс для централизованного управления путями и определением типа окружения.

    Атрибуты класса:
        PROJECT_ROOT (Path): Корневая директория проекта.
        APP_DIR (Path): Директория с исходным кодом приложения (src).
        CORE_DIR (Path): Директория с ядром приложения (src/core).

    Методы:
        find_project_root(): Определяет корень проекта по маркерным файлам.
        get_env_file_and_type(): Определяет используемый env-файл и тип окружения.
    """

    @staticmethod
    def find_project_root() -> Path:
        """
        Находит корень проекта по маркерным файлам.

        Алгоритм:
        - Начинает поиск с текущей рабочей директории.
        - Поднимается вверх по дереву директорий.
        - Если находит хотя бы один из маркерных файлов (.git, pyproject.toml, README.md), возвращает эту директорию.
        - Если ни один маркер не найден, возвращает текущую директорию и пишет предупреждение в лог.

        Returns:
            Path: Путь к корню проекта.
        """
        current_dir = Path.cwd()

        # Маркерные файлы, которые обычно есть в корне проекта
        markers = [".git", "pyproject.toml", "README.md"]

        # Ищем маркеры, поднимаясь по директориям
        for parent in [current_dir, *current_dir.parents]:
            if any((parent / marker).exists() for marker in markers):
                return parent

        logger.warning(
            "Не удалось определить корень проекта, используем текущую директорию"
        )
        return current_dir

    PROJECT_ROOT: ClassVar[Path] = find_project_root()

    APP_DIR: ClassVar[Path] = PROJECT_ROOT / "src"
    CORE_DIR: ClassVar[Path] = APP_DIR / "core"
    TEMPLATES_DIR: ClassVar[Path] = CORE_DIR / "templates"
    EMAIL_TEMPLATES_DIR: ClassVar[Path] = TEMPLATES_DIR / "mail"

    @staticmethod
    def get_env_file_and_type() -> tuple[Path, str]:
        """
        Определяет путь к файлу с переменными окружения и тип окружения.

        Алгоритм:
        - Если переменная окружения ENV_FILE задана, используется указанный путь.
          - Если имя файла содержит ".env.test", считается что это тестовое окружение.
          - В противном случае — кастомное окружение.
        - Если в корне проекта есть .env.dev, используется он и считается development-окружением.
        - В остальных случаях используется .env и считается production-окружением.

        Returns:
            tuple[Path, str]: Путь к файлу с переменными окружения и тип окружения (development/production/test/custom).
        """
        ENV_FILE = Path(".env")
        DEV_ENV_FILE = Path(".env.dev")

        # Определяем конфигурацию
        env_file_path = os.getenv("ENV_FILE")
        if env_file_path:
            env_path = Path(env_file_path)
            if ".env.test" in str(env_path):
                env_type = "test"
            else:
                env_type = "custom"
        elif DEV_ENV_FILE.exists():
            env_path = DEV_ENV_FILE
            env_type = "development"
        else:
            env_path = ENV_FILE
            env_type = "production"
        logger.info("Запуск в режиме: %s", env_type.upper())
        logger.info("Конфигурация: %s", env_path)

        return env_path, env_type


class LoggingSettings(BaseSettings):
    """
    Конфигурация логирования приложения.

    Атрибуты:
        LOG_LEVEL (str): Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        LOG_FORMAT (str): Формат логирования (pretty, json, simple).
        LOG_FILE (str): Путь к файлу логов.
        MAX_BYTES (int): Максимальный размер файла логов для ротации.
        BACKUP_COUNT (int): Количество резервных копий логов.
        ENCODING (str): Кодировка файла логов.
        FILE_MODE (str): Режим открытия файла логов.
        CONSOLE_ENABLED (bool): Включено ли логирование в консоль.
        FILE_FORMAT (str): Формат для файлового логирования.
        PRETTY_FORMAT (str): Цветной формат для консоли.
        SIMPLE_FORMAT (str): Краткий формат для консоли.

    Свойства и методы:
        current_format: Текущий формат логирования.
        is_json_format: Используется ли JSON формат.
        log_dir: Директория для логов.
        ensure_log_dir(): Создаёт директорию для логов, если не существует.
        file_handler_config: Конфиг для файлового обработчика.
        console_handler_config: Конфиг для консольного обработчика.
        to_dict(): Конфиг логирования в виде словаря.
        logging_config: Полная конфигурация для logging.dictConfig().
    """

    LOG_LEVEL: str = "DEBUG"
    LOG_FORMAT: str = "pretty"  # pretty, json, simple
    LOG_FILE: str = "./logs/app.log" if os.name == "nt" else "/var/log/app.log"
    MAX_BYTES: int = 10485760  # 10MB
    BACKUP_COUNT: int = 5
    ENCODING: str = "utf-8"
    FILE_MODE: str = "a"

    CONSOLE_ENABLED: bool = True

    FILE_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    PRETTY_FORMAT: str = (
        "\033[1;36m%(asctime)s\033[0m - \033[1;32m%(name)s\033[0m - "
        "\033[1;33m%(levelname)s\033[0m - %(message)s"
    )

    JSON_FORMAT: dict = {
        "timestamp": "%(asctime)s",
        "level": "%(levelname)s",
        "module": "%(module)s",
        "func": "%(funcName)s",
        "message": "%(message)s",
    }

    SIMPLE_FORMAT: str = "%(levelname)s - %(name)s - %(message)s"

    @property
    def current_format(self) -> str:
        """Возвращает текущий формат логирования"""
        format_map = {
            "pretty": self.PRETTY_FORMAT,
            "simple": self.SIMPLE_FORMAT,
            "json": self.FILE_FORMAT,  # Для JSON используем базовый формат
        }
        return format_map.get(self.LOG_FORMAT, self.FILE_FORMAT)

    @property
    def is_json_format(self) -> bool:
        """Проверяет, используется ли JSON формат"""
        return self.LOG_FORMAT.lower() == "json"

    @property
    def log_dir(self) -> str:
        """Возвращает директорию для логов"""
        return os.path.dirname(self.LOG_FILE)

    def ensure_log_dir(self) -> None:
        """Создает директорию для логов если она не существует"""
        log_dir = self.log_dir
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

    @property
    def file_handler_config(self) -> Dict[str, Any]:
        """Конфигурация для файлового обработчика логов"""
        return {
            "filename": self.LOG_FILE,
            "maxBytes": self.MAX_BYTES,
            "backupCount": self.BACKUP_COUNT,
            "encoding": self.ENCODING,
            "mode": self.FILE_MODE,
        }

    @property
    def console_handler_config(self) -> Dict[str, Any]:
        """Конфигурация для консольного обработчика логов"""
        return {
            "stream": "ext://sys.stdout",
        }

    def to_dict(self) -> Dict[str, Any]:
        """Возвращает конфигурацию в виде словаря для настройки логирования"""
        return {
            "level": self.LOG_LEVEL,
            "format": self.current_format,
            "is_json": self.is_json_format,
            "console_enabled": self.CONSOLE_ENABLED,
            "file_config": self.file_handler_config,
            "console_config": self.console_handler_config,
        }

    @property
    def logging_config(self) -> Dict[str, Any]:
        """
        Полная конфигурация для logging.dictConfig().

        Формирует структуру для dictConfig с учётом выбранного формата, ротации файлов и консольного вывода.
        """
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": self.current_format,
                },
            },
            "handlers": {},
            "root": {
                "level": self.LOG_LEVEL,
                "handlers": [],
            },
        }

        # Добавляем файловый обработчик
        if self.LOG_FILE:
            self.ensure_log_dir()
            config["handlers"]["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "default",
                **self.file_handler_config,
            }
            config["root"]["handlers"].append("file")

        # Добавляем консольный обработчик
        if self.CONSOLE_ENABLED:
            config["handlers"]["console"] = {
                "class": "logging.StreamHandler",
                "formatter": "default",
                **self.console_handler_config,
            }
            config["root"]["handlers"].append("console")

        # Для JSON формата добавляем специальный форматтер
        if self.is_json_format:
            config["formatters"]["json"] = {
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(module)s %(funcName)s %(message)s",
            }
            # Применяем JSON форматтер ко всем обработчикам
            for handler in config["handlers"].values():
                handler["formatter"] = "json"

        return config


env_file_path, app_env = PathSettings.get_env_file_and_type()


class Settings(BaseSettings):
    """
    Главный класс настроек приложения.

    Атрибуты:
        logging (LoggingSettings): Настройки логирования.
        paths (PathSettings): Пути и параметры окружения.
        tokens (TokenSettings): Настройки токенов и аутентификации.
        cors (CorsSettings): Настройки CORS.
        database (DatabaseSettings): Настройки подключения к БД.

        TITLE (str): Название микросервиса.
        DESCRIPTION (str): Описание микросервиса.
        VERSION (str): Версия приложения.
        HOST (str): Хост для запуска (обычно 0.0.0.0).
        PORT (int): Порт для запуска (обычно 8000).

    Свойства:
        app_params (dict): Параметры для FastAPI.
        uvicorn_params (dict): Параметры для запуска uvicorn (только для разработки).
    """

    # Виртуальное окружение приложения
    app_env: str = app_env

    logging: LoggingSettings = LoggingSettings()
    paths: PathSettings = PathSettings()

    # Настройки микросервиса
    TITLE: str = "NoRake Backend Service"
    DESCRIPTION: str = "API NoRake Backend Service"
    VERSION: str = "0.1.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @property
    def app_params(self) -> dict:
        """
        Параметры для инициализации FastAPI приложения.

        Returns:
            Dict с настройками FastAPI
        """
        return {
            "title": self.TITLE,
            "description": self.DESCRIPTION,
            "version": self.VERSION,
            "swagger_ui_parameters": {"defaultModelsExpandDepth": -1},
            "root_path": "",
            "lifespan": lifespan,
        }

    @property
    def uvicorn_params(self) -> dict:
        """
        Параметры для запуска uvicorn сервера.

        Returns:
            Dict с настройками uvicorn
        """
        return {
            "host": self.HOST,
            "port": self.PORT,
            "proxy_headers": True,
            "forwarded_allow_ips": "*",  # Доверять всем прокси (для Traefik)
            "log_level": "debug",
        }

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DATABASE: str

    @property
    def database_dsn(self) -> PostgresDsn:
        """
        Создает DSN для подключения к PostgreSQL.

        Returns:
            PostgresDsn: DSN для подключения к PostgreSQL.
        """
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD.get_secret_value(),  # :)
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DATABASE,
        )

    @property
    def database_url(self) -> str:
        """
        Строка подключения к базе данных (используется Alembic и SQLAlchemy).

        Returns:
            str: Строка подключения к базе данных.
        """
        return str(self.database_dsn)

    @property
    def engine_params(self) -> Dict[str, Any]:
        """
        Параметры для создания SQLAlchemy engine.

        Returns:
            dict: Параметры подключения к PostgreSQL.
        """
        return {
            "echo": False,  # Логирование SQL-запросов (для отладки)
        }

    @property
    def session_params(self) -> Dict[str, Any]:
        """
        Параметры для создания SQLAlchemy session.

        Returns:
            dict: Параметры подключения к PostgreSQL.
        """
        return {
            "autocommit": False,  # Автоматическое подтверждение транзакций для сессии
            "autoflush": False,  # Автоматическая очистка буфера перед выполнением запроса
            "expire_on_commit": False,  # Не инвалидировать объекты после коммита (чтобы избежать лишних запросов к БД)
            "class_": AsyncSession,
        }


    # Настройки Redis
    REDIS_USER: str = "default"
    REDIS_PASSWORD: SecretStr
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DATABASE: int = 0
    REDIS_POOL_SIZE: int = 10

    @property
    def redis_dsn(self) -> RedisDsn:
        """
        Создает DSN для подключения к Redis.

        Returns:
            RedisDsn: DSN для подключения к Redis.
        """
        return RedisDsn.build(
            scheme="redis",
            username=self.REDIS_USER,
            password=self.REDIS_PASSWORD.get_secret_value(),
            host=self.REDIS_HOST,
            port=self.REDIS_PORT,
            path=f"/{self.REDIS_DATABASE}",
        )

    @property
    def redis_url(self) -> str:
        """
        Строковое представление DSN для подключения к Redis.

        returns:
            str: Строка подключения к Redis.
        """
        return str(self.redis_dsn)

    @property
    def redis_params(self) -> Dict[str, Any]:
        """
        Параметры для создания Redis connection pool.

        Returns:
            dict: Параметры подключения к Redis.
        """
        return {"url": self.redis_url, "max_connections": self.REDIS_POOL_SIZE}

    # Настройки RabbitMQ
    RABBITMQ_CONNECTION_TIMEOUT: int = 30
    RABBITMQ_EXCHANGE: str = "profitool_exchange"
    RABBITMQ_USER: str
    RABBITMQ_PASS: SecretStr
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5673

    @property
    def rabbitmq_dsn(self) -> AmqpDsn:
        return AmqpDsn.build(
            scheme="amqp",
            username=self.RABBITMQ_USER,
            password=self.RABBITMQ_PASS.get_secret_value(),
            host=self.RABBITMQ_HOST,
            port=self.RABBITMQ_PORT,
        )

    @property
    def rabbitmq_url(self) -> str:
        """
        Для pika нужно строку с подключением к RabbitMQ
        """
        return str(self.rabbitmq_dsn)

    @property
    def rabbitmq_params(self) -> Dict[str, Any]:
        """
        Формирует параметры подключения к RabbitMQ.

        Returns:
            Dict с параметрами подключения к RabbitMQ
        """
        return {
            "url": self.rabbitmq_url,
            "connection_timeout": self.RABBITMQ_CONNECTION_TIMEOUT,
            "exchange": self.RABBITMQ_EXCHANGE,
        }

    # Настройки S3/MinIO Storage
    AWS_SERVICE_NAME: str = "s3"
    AWS_REGION: str = "us-east-1"
    AWS_ENDPOINT: Optional[str] = None  # MinIO endpoint для локальной разработки
    AWS_BUCKET_NAME: str = "norake-documents"
    AWS_ACCESS_KEY_ID: SecretStr
    AWS_SECRET_ACCESS_KEY: SecretStr

    @property
    def s3_params(self) -> Dict[str, Any]:
        """
        Формирует параметры подключения к S3/MinIO.

        Returns:
            Dict с параметрами подключения к S3
        """
        params = {
            "service_name": self.AWS_SERVICE_NAME,
            "region_name": self.AWS_REGION,
            "aws_access_key_id": self.AWS_ACCESS_KEY_ID.get_secret_value(),
            "aws_secret_access_key": self.AWS_SECRET_ACCESS_KEY.get_secret_value(),
        }
        if self.AWS_ENDPOINT:
            params["endpoint_url"] = self.AWS_ENDPOINT
        return params

    # Настройки Document Services
    DOCUMENT_MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50 MB
    DOCUMENT_BASE_URL: str = "http://localhost:8000"  # Базовый URL приложения
    
    # Разрешённые MIME типы для загрузки документов (ключи соответствуют DocumentFileType.value)
    DOCUMENT_ALLOWED_MIME_TYPES: Dict[str, List[str]] = {
        "pdf": ["application/pdf"],
        "spreadsheet": [
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ],
        "text": [
            "text/plain",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ],
        "image": [
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
        ],
    }

    # Настройки аутентификации

    # Секретный ключ для токенов
    TOKEN_SECRET_KEY: SecretStr

    # Настройки токенов
    TOKEN_TYPE: str = "Bearer"
    TOKEN_ALGORITHM: str = "HS256"

    # Пути для куки
    ACCESS_TOKEN_PATH: str = "/"
    REFRESH_TOKEN_PATH: str = "/"

    # Время жизни токенов (в минутах/днях)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30


    @property
    def ACCESS_TOKEN_MAX_AGE(self) -> int:
        """Время жизни access токена в секундах."""
        return self.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    @property
    def REFRESH_TOKEN_MAX_AGE(self) -> int:
        """Время жизни refresh токена в секундах."""
        return self.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60



    # Настройки паролей
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPER: bool = True
    PASSWORD_REQUIRE_LOWER: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    PASSWORD_FORBID_USERNAME: bool = True
    PASSWORD_COMMON_SEQUENCES: List[str] = [
        "12345",
        "qwerty",
        "password",
        "admin",
        "123456789",
        "abc123",
    ]

    # Параметры хеширования Argon2
    PASSWORD_HASH_SCHEME: str = "argon2"
    ARGON2_TIME_COST: int = 2
    ARGON2_MEMORY_COST: int = 102400
    ARGON2_PARALLELISM: int = 8

    # Настройки фикстур
    LOAD_FIXTURES: bool = False  # Загружать ли фикстуры при старте приложения

    @property
    def crypt_context_params(self) -> Dict[str, Any]:
        """
        Параметры для CryptContext из passlib.

        Returns:
            Dict с настройками для Argon2 хеширования
        """
        return {
            "schemes": [self.PASSWORD_HASH_SCHEME],
            "deprecated": "auto",
            "argon2__time_cost": self.ARGON2_TIME_COST,
            "argon2__memory_cost": self.ARGON2_MEMORY_COST,
            "argon2__parallelism": self.ARGON2_PARALLELISM,
        }

    # Настройки куки
    # Для cross-site (localhost -> api.norake.ru): SameSite=None, Secure=False (HTTP dev)
    # Для production (HTTPS): SameSite=None, Secure=True
    COOKIE_DOMAIN: Optional[str] = None
    COOKIE_SECURE: bool = False  # False для HTTP localhost, True для HTTPS production
    COOKIE_SAMESITE: str = "None"  # None для cross-site, Lax/Strict для same-site
    COOKIE_HTTPONLY: bool = True  # True для защиты от XSS

    @property
    def access_token_cookie_params(self) -> Dict[str, Any]:
        """Параметры для access_token куки."""
        return {
            "domain": self.COOKIE_DOMAIN,
            "secure": self.COOKIE_SECURE,
            "samesite": self.COOKIE_SAMESITE,
            "httponly": self.COOKIE_HTTPONLY,
            "path": self.ACCESS_TOKEN_PATH,
            "max_age": self.ACCESS_TOKEN_MAX_AGE,
        }

    @property
    def refresh_token_cookie_params(self) -> Dict[str, Any]:
        """Параметры для refresh_token куки."""
        return {
            "domain": self.COOKIE_DOMAIN,
            "secure": self.COOKIE_SECURE,
            "samesite": self.COOKIE_SAMESITE,
            "httponly": self.COOKIE_HTTPONLY,
            "path": self.REFRESH_TOKEN_PATH,
            "max_age": self.REFRESH_TOKEN_MAX_AGE,
        }

    # Настройки методов аутентификации
    USERNAME_ALLOWED_TYPES: List[str] = ["email", "phone", "username"]

    @field_validator("USERNAME_ALLOWED_TYPES", mode="before")
    @classmethod
    def parse_allowed_types(cls, v):
        """
        Преобразование строки в список, если передано как строка.

        Args:
            v: Значение, которое может быть строкой или списком.

        Returns:
            List[str]: Список разрешённых типов.
        """
        if isinstance(v, str):
            return [t.strip() for t in v.split(",")]
        return v

    # Дефолтный админ (обязательный)
    # Создаётся автоматически при первом запуске, если не существует
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_EMAIL: EmailStr = "admin@norake.ru"
    DEFAULT_ADMIN_PASSWORD: SecretStr

    # Дополнительные админы (опционально)
    # Формат: username:email:password,username2:email2:password2
    # Пример: ADMINS=mike:mike@norake.ru:SecurePass123,anna:anna@norake.ru:AnotherPass456
    ADMINS: Optional[str] = None

    @property
    def additional_admins(self) -> List[Dict[str, str]]:
        """
        Парсинг дополнительных админов из ENV переменной ADMINS.

        Returns:
            List[Dict]: Список словарей с данными админов
                [{"username": "mike", "email": "mike@norake.ru", "password": "Pass123"}, ...]
        """
        if not self.ADMINS:
            return []

        admins = []
        for admin_str in self.ADMINS.split(","):
            parts = admin_str.strip().split(":")
            if len(parts) == 3:
                admins.append({
                    "username": parts[0].strip(),
                    "email": parts[1].strip(),
                    "password": parts[2].strip(),
                })
            else:
                logger.warning(
                    "⚠️ Неверный формат админа: '%s'. Ожидается 'username:email:password'",
                    admin_str
                )
        return admins

    # Настройки доступа в docs/redoc
    DOCS_ACCESS: bool = True
    DOCS_USERNAME: str = "admin"
    DOCS_PASSWORD: SecretStr

    # Настройки безопасности
    TOKEN_SECRET_KEY: SecretStr

    # Настройки OpenRouter AI Integration
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_EMBEDDING_MODEL: str = "openai/text-embedding-ada-002"
    OPENROUTER_TIMEOUT: int = 30
    OPENROUTER_MAX_RETRIES: int = 3

    # Настройки n8n Integration
    N8N_BASE_URL: str = "http://localhost:5678"
    N8N_API_KEY: Optional[SecretStr] = None
    N8N_WEBHOOK_TIMEOUT: int = 30
    N8N_WEBHOOK_RETRY_ATTEMPTS: int = 2
    N8N_WEBHOOK_RETRY_DELAY: float = 1.0

    # Настройки поиска (NORAK-40)
    # Приоритеты для ранжирования источников поиска
    SEARCH_PRIORITY_DB: float = 1.0
    SEARCH_PRIORITY_RAG: float = 0.8
    SEARCH_PRIORITY_MCP: float = 0.6

    # TTL для Redis кеша результатов поиска (в секундах)
    SEARCH_CACHE_TTL: int = 300

    # URL webhook для n8n smart search helper (опционально)
    N8N_SMART_SEARCH_WEBHOOK: Optional[str] = None

    # Настройки DB поиска
    # Максимальное количество результатов из БД
    DB_SEARCH_LIMIT: int = 50
    # Score эвристика для DB поиска (на основе местоположения совпадения)
    DB_SEARCH_SCORE_TITLE: float = 1.0  # Совпадение в заголовке
    DB_SEARCH_SCORE_DESCRIPTION: float = 0.8  # Совпадение в описании
    DB_SEARCH_SCORE_OTHER: float = 0.6  # Совпадение в других полях

    # Настройки RAG поиска
    # Дефолтное количество результатов из векторного поиска
    RAG_SEARCH_LIMIT: int = 5
    # Минимальный порог cosine similarity (0-1)
    RAG_MIN_SIMILARITY: float = 0.7
    # Количество результатов для reranking
    RAG_RERANK_TOP_K: int = 3

    # Категории Issue и Template (синхронизированы с n8n workflow)
    # TODO: Переделать в CategoryModel в БД + admin API для управления
    ISSUE_CATEGORIES: List[str] = [
        "hardware",
        "software",
        "process",
        "documentation",
        "safety",
        "quality",
        "maintenance",
        "training",
        "other",
    ]

    # Настройки CORS
    ALLOW_ORIGINS: List[str] = [
        "https://norake.ru",
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    ALLOW_CREDENTIALS: bool = True
    ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    ALLOW_HEADERS: List[str] = [
        "accept",
        "accept-encoding",
        "authorization",
        "content-type",
        "dnt",
        "origin",
        "user-agent",
        "x-csrftoken",
        "x-requested-with",
        "manifest-fetch-site",
    ]

    @property
    def cors_params(self) -> dict:
        return {
            "allow_origins": self.ALLOW_ORIGINS,
            "allow_credentials": self.ALLOW_CREDENTIALS,
            "allow_methods": self.ALLOW_METHODS,
            "allow_headers": self.ALLOW_HEADERS,
        }

    model_config = SettingsConfigDict(
        env_file=env_file_path,
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="allow",
    )


# Глобальный экземпляр настроек
settings = Settings()
