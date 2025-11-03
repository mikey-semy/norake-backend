"""
Базовые схемы для аутентификации и авторизации в API v1.

Этот модуль содержит основные Pydantic схемы для работы с системой аутентификации
и авторизации пользователей. Схемы обеспечивают валидацию данных и типизацию
на границах API и внутри приложения.

Основные группы схем:
    - Токены: TokenDataSchema для JWT токенов
    - Восстановление пароля: PasswordResetDataSchema, PasswordResetConfirmDataSchema
    - Пользователи: UserSchema, UserCurrentSchema, UserCredentialsSchema
    - Системные: LogoutDataSchema для логирования выходов

Безопасность:
    UserCredentialsSchema содержит хешированный пароль и предназначена ТОЛЬКО
    для внутреннего использования. Никогда не возвращайте её в API ответах!

Использование:
    >>> # Валидация токенов
    >>> token_data = TokenDataSchema(
    ...     access_token="jwt_token_here",
    ...     refresh_token="refresh_token_here",
    ...     expires_in=3600
    ... )
    
    >>> # Текущий пользователь
    >>> current_user = UserCurrentSchema(
    ...     id=uuid4(),
    ...     username="alice",
    ...     email="alice@example.com",
    ...     role="user"
    ... )

Note:
    Все схемы наследуются от CommonBaseSchema и используют Field() для
    детального описания полей и валидации.

See Also:
    - src.schemas.v1.auth.requests: Схемы для входящих запросов
    - src.schemas.v1.auth.responses: Схемы для HTTP ответов
    - src.core.security: Модули для работы с токенами и паролями
"""

import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from src.schemas.base import CommonBaseSchema


__all__ = [
    "TokenDataSchema",
    "LogoutDataSchema", 
    "PasswordResetDataSchema",
    "PasswordResetConfirmDataSchema",
    "UserCredentialsSchema",
    "UserSchema",
    "UserCurrentSchema",
]


class TokenDataSchema(CommonBaseSchema):
    """
    Схема данных токенов аутентификации JWT.

    Используется для возврата токенов клиенту после успешной аутентификации
    и для внутренней передачи данных о токенах между сервисами.

    Attributes:
        access_token: JWT токен для авторизации API запросов
        refresh_token: Токен для получения нового access_token
        token_type: Тип токена (всегда "Bearer" для JWT)
        expires_in: Время жизни access_token в секундах

    Example:
        >>> token_data = TokenDataSchema(
        ...     access_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        ...     refresh_token="def50200...",
        ...     expires_in=3600
        ... )
        >>> print(f"Токен истекает через {token_data.expires_in} секунд")

    Note:
        Время expires_in указывается в секундах от момента создания токена.
        Клиент должен обновить токен до истечения этого времени.
    """

    access_token: str = Field(description="JWT токен доступа для авторизации запросов")
    refresh_token: str = Field(description="Токен для обновления access_token")
    token_type: str = Field(default="Bearer", description="Тип токена для заголовка Authorization")
    expires_in: int = Field(description="Время жизни access_token в секундах")


class LogoutDataSchema(CommonBaseSchema):
    """
    Схема данных успешного выхода из системы.

    Возвращается клиенту при успешном выполнении операции logout.
    Содержит временную метку для логирования и аудита.

    Attributes:
        logged_out_at: Точная временная метка выхода в UTC

    Example:
        >>> from datetime import datetime
        >>> logout_data = LogoutDataSchema(
        ...     logged_out_at=datetime.utcnow()
        ... )
        >>> print(f"Пользователь вышел: {logout_data.logged_out_at}")

    Note:
        Время всегда сохраняется в UTC для избежания проблем с часовыми поясами.
        При отображении пользователю конвертируйте в локальное время.
    """

    logged_out_at: datetime = Field(description="Время выхода из системы в формате UTC")


class PasswordResetDataSchema(CommonBaseSchema):
    """
    Схема данных запроса сброса пароля.

    Возвращается после успешной отправки ссылки восстановления пароля.
    Содержит информацию о времени действия ссылки для уведомления пользователя.

    Attributes:
        email: Email адрес, на который отправлена ссылка восстановления
        expires_in: Время действия ссылки в секундах

    Example:
        >>> reset_data = PasswordResetDataSchema(
        ...     email="user@example.com",
        ...     expires_in=3600
        ... )
        >>> print(f"Ссылка отправлена на {reset_data.email}")
        >>> print(f"Действительна {reset_data.expires_in // 60} минут")

    Security:
        Не возвращайте токен восстановления в этой схеме! Токен отправляется
        только на email и не должен попадать в HTTP ответы.
    """

    email: EmailStr = Field(description="Email адрес для восстановления пароля")
    expires_in: int = Field(description="Время действия ссылки восстановления в секундах")


class PasswordResetConfirmDataSchema(CommonBaseSchema):
    """
    Схема данных подтверждения сброса пароля.

    Возвращается после успешной смены пароля через ссылку восстановления.
    Подтверждает, что операция выполнена и фиксирует время изменения.

    Attributes:
        password_changed_at: Точное время изменения пароля в UTC

    Example:
        >>> from datetime import datetime
        >>> confirm_data = PasswordResetConfirmDataSchema(
        ...     password_changed_at=datetime.utcnow()
        ... )
        >>> print(f"Пароль изменен: {confirm_data.password_changed_at}")

    Note:
        После смены пароля все активные токены пользователя должны быть
        аннулированы для обеспечения безопасности.
    """

    password_changed_at: datetime = Field(description="Время изменения пароля в формате UTC")


class UserCredentialsSchema(CommonBaseSchema):
    """
    Схема полных учетных данных пользователя с паролем.

    ⚠️ КРИТИЧЕСКИ ВАЖНО: ТОЛЬКО для внутреннего использования!
    ⚠️ НИКОГДА не возвращайте в API ответах!
    ⚠️ Содержит хешированный пароль!

    Используется для:
    - Внутренней передачи данных между сервисами
    - Валидации учетных данных при аутентификации
    - Сохранения в кэше (Redis) после аутентификации

    Attributes:
        id: Уникальный идентификатор пользователя
        username: Уникальное имя пользователя для входа
        email: Email адрес пользователя (валидированный)
        password_hash: Хешированный пароль (bcrypt/argon2)
        is_active: Флаг активности аккаунта
        role: Роль пользователя в системе

    Example:
        >>> # ТОЛЬКО внутри сервисов!
        >>> credentials = UserCredentialsSchema(
        ...     id=uuid4(),
        ...     username="alice",
        ...     email="alice@example.com",
        ...     password_hash="$2b$12$...",
        ...     is_active=True,
        ...     role="user"
        ... )

    Security:
        - password_hash должен быть результатом bcrypt/argon2
        - Схема не должна попадать в HTTP ответы
        - При сериализации для логов исключите password_hash
    """

    id: uuid.UUID = Field(description="ID пользователя")
    username: str = Field(description="Уникальное имя пользователя")
    email: EmailStr = Field(description="Email пользователя")
    password_hash: str = Field(description="Хешированный пароль")
    is_active: bool = Field(description="Активность аккаунта")
    role: str = Field(default="user", description="Роль (admin/user)")


class UserSchema(CommonBaseSchema):
    """
    Схема безопасного представления пользователя без пароля.

    Используется для внутренней передачи данных пользователя между сервисами,
    кэширования в Redis и других случаев, где не нужен пароль.

    Отличия от UserCredentialsSchema:
    - НЕ содержит password_hash (безопасно)
    - Можно использовать в логах и отладке
    - Подходит для кэширования

    Attributes:
        id: Уникальный идентификатор пользователя
        username: Уникальное имя пользователя
        email: Email адрес пользователя (валидированный)
        is_active: Флаг активности аккаунта
        role: Роль пользователя в системе

    Example:
        >>> user = UserSchema(
        ...     id=uuid4(),
        ...     username="alice",
        ...     email="alice@example.com",
        ...     is_active=True,
        ...     role="user"
        ... )
        >>> # Безопасно для кэширования в Redis
        >>> redis.set(f"user:{user.id}", user.model_dump_json())

    Use Cases:
        - Кэширование в Redis через AuthRedisManager
        - Передача между внутренними сервисами
        - Логирование пользовательских действий
        - Валидация ролей и прав доступа
    """

    id: uuid.UUID = Field(description="ID пользователя")
    username: str = Field(description="Уникальное имя пользователя")
    email: EmailStr = Field(description="Email пользователя")
    is_active: bool = Field(description="Активность аккаунта")
    role: str = Field(default="user", description="Роль (admin/user)")


class UserCurrentSchema(CommonBaseSchema):
    """
    Схема текущего аутентифицированного пользователя для API ответов.

    Используется для возврата информации о текущем пользователе клиенту.
    Содержит минимальный набор данных, необходимых фронтенду.

    Отличия от других пользовательских схем:
    - Только публичная информация
    - Оптимизирована для API ответов
    - Не содержит системных полей (is_active)

    Attributes:
        id: Уникальный идентификатор пользователя
        username: Имя пользователя для отображения
        email: Email адрес пользователя
        role: Роль для определения прав в UI

    Example:
        >>> # В API endpoint /auth/me
        >>> current_user = UserCurrentSchema(
        ...     id=uuid4(),
        ...     username="alice",
        ...     email="alice@example.com",
        ...     role="user"
        ... )
        >>> return {"success": True, "data": current_user}

    Frontend Usage:
        Фронтенд использует эти данные для:
        - Отображения имени пользователя в header
        - Показа/скрытия элементов UI по роли
        - Предзаполнения форм профиля
    """

    id: uuid.UUID = Field(description="ID пользователя")
    username: str = Field(description="Уникальное имя пользователя")
    email: EmailStr = Field(description="Email пользователя")
    role: str = Field(description="Роль пользователя (admin/user)")

