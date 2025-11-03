"""
Зависимости для сервиса аутентификации.

Этот модуль содержит провайдер (фабрику) для создания экземпляра сервиса
аутентификации с автоматическим внедрением зависимостей через FastAPI Depends.

Providers:
    - get_auth_service: Провайдер для AuthService

Typed Dependencies:
    - AuthServiceDep: Типизированная зависимость для AuthService

Usage:
    ```python
    from src.core.dependencies import AuthServiceDep

    @router.post("/auth/login")
    async def login(
        auth_service: AuthServiceDep,
        form_data: OAuth2PasswordRequestForm = Depends(),
    ) -> TokenResponseSchema:
        return await auth_service.authenticate(form_data)
    ```
"""

import logging
from typing import Annotated

from fastapi import Depends

from src.core.dependencies.database import AsyncSessionDep
from src.core.dependencies.cache import RedisDep
from src.services.v1.auth import AuthService

logger = logging.getLogger(__name__)


async def get_auth_service(
    session: AsyncSessionDep,
    redis: RedisDep,
) -> AuthService:
    """
    Провайдер для AuthService.

    Создает экземпляр AuthService с внедренными зависимостями:
    - Сессия базы данных (для работы с UserModel)
    - Redis клиент (для хранения токенов и blacklist)

    Args:
        session: Асинхронная сессия базы данных.
        redis: Redis клиент для работы с токенами.

    Returns:
        AuthService: Настроенный экземпляр сервиса аутентификации.

    Raises:
        ServiceUnavailableException: Если не удается создать сервис.

    Example:
        ```python
        # Автоматическое внедрение через FastAPI
        @router.post("/auth/login")
        async def login(
            auth_service: AuthServiceDep,
            form_data: OAuth2PasswordRequestForm = Depends(),
        ):
            return await auth_service.authenticate(form_data)
        ```
    """
    try:
        logger.debug("Создание экземпляра AuthService")
        return AuthService(session=session, redis=redis)
    except Exception as e:
        logger.error(
            "Ошибка при создании AuthService: %s", str(e), exc_info=True
        )
        raise


# Типизированная зависимость для удобства использования
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
