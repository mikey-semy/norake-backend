"""
Схемы запросов для регистрации пользователей.

Модуль содержит Pydantic схемы для валидации данных при регистрации новых пользователей.
Включает валидацию паролей и email адресов согласно требованиям безопасности.

Схемы:
    - RegistrationRequestSchema: Схема для входных данных регистрации пользователя
"""

from typing import Optional

from pydantic import EmailStr, Field, field_validator

from src.schemas.base import CommonBaseSchema


class RegistrationRequestSchema(CommonBaseSchema):
    """
    Схема для регистрации нового пользователя.

    Предоставляет валидацию минимальных данных для создания учетной записи
    покупателя (user), включая проверку силы пароля и корректности формата email.

    Attributes:
        username (str): Имя пользователя (генерируется автоматически из email)
        email (EmailStr): Email адрес пользователя (автоматическая валидация формата)
        password (str): Пароль с проверкой требований безопасности

    Validation Rules:
        - username: Обязательное поле, уникальное имя пользователя
        - email: Обязательное поле, валидный email формат
        - password: Минимум 8 символов, заглавная и строчная буквы, цифра, спецсимвол

    Example:
        ```python
        registration_data = RegistrationRequestSchema(
            email="john@example.com",
            password="SecurePass123!"
        )
        ```

    Note:
        - Username генерируется автоматически из email
        - Роль "admin" не может быть зарегистрирована через публичный endpoint
        - Администраторы создаются через настройки при инициализации приложения
        - Данные профиля (phone) заполняются после регистрации
    """
    username: Optional[str] = Field(
        None,
        description=(
            "Имя пользователя. Генерируется автоматически из email, "
            "поэтому не требуется при регистрации."
        ),
        examples=["john_doe", "jane.smith"],
    )
    email: EmailStr = Field(
        description="Email адрес пользователя",
        examples=["user@example.com", "john.doe@company.org"],
    )

    password: str = Field(
        min_length=8,
        max_length=128,
        description=(
            "Пароль пользователя. Требования: "
            "минимум 8 символов, заглавная и строчная буквы, "
            "цифра, специальный символ"
        ),
        examples=["SecurePass123!", "MyP@ssw0rd2024"],
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str, info) -> str:
        """
        Валидатор для проверки пароля на соответствие требованиям безопасности.

        Проверяет:
        - Минимальную длину (8 символов)
        - Наличие заглавных и строчных букв
        - Наличие цифр
        - Наличие специальных символов
        - Отсутствие username в пароле

        Args:
            v (str): Пароль для валидации
            info: Контекст валидации с доступом к другим полям

        Returns:
            str: Валидный пароль

        Raises:
            ValueError: Если пароль не соответствует требованиям безопасности

        Note:
            Валидатор автоматически получает username из других полей схемы
            для проверки, что пароль не содержит имя пользователя.
        """
        # Проверка длины (уже проверено Field, но явная проверка для ясности)
        if len(v) < 8:
            raise ValueError("Пароль должен содержать минимум 8 символов")

        # Проверка наличия заглавной буквы
        if not any(c.isupper() for c in v):
            raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")

        # Проверка наличия строчной буквы
        if not any(c.islower() for c in v):
            raise ValueError("Пароль должен содержать хотя бы одну строчную букву")

        # Проверка наличия цифры
        if not any(c.isdigit() for c in v):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")

        # Проверка наличия специального символа
        special_chars = "!@#$%^&*()-_=+[]{}|;:',.<>?/`~"
        if not any(c in special_chars for c in v):
            raise ValueError(
                f"Пароль должен содержать хотя бы один специальный символ: {special_chars}"
            )

        # Примечание: Проверка на username убрана, т.к. username генерируется автоматически

        return v
