"""
Зависимости для сервиса регистрации.

Этот модуль содержит провайдер (фабрику) для создания экземпляра сервиса
регистрации с автоматическим внедрением зависимостей через FastAPI Depends.

Providers:
    - get_register_service: Провайдер для RegisterService

Typed Dependencies:
    - RegisterServiceDep: Типизированная зависимость для RegisterService

Usage:
    ```python
    from src.core.dependencies import RegisterServiceDep

    @router.post("/register")
    async def register_user(
        register_service: RegisterServiceDep,
        new_user: RegistrationRequestSchema,
    ) -> RegistrationResponseSchema:
        return await register_service.create_user(new_user)
    ```
"""

import logging
from typing import Annotated

from fastapi import Depends

from src.core.dependencies.database import AsyncSessionDep
from src.services import RegisterService

logger = logging.getLogger(__name__)


async def get_register_service(
    session: AsyncSessionDep,
) -> RegisterService:
    """
    Провайдер для RegisterService.

    Создает экземпляр RegisterService с внедренными зависимостями:
    - Сессия базы данных (для работы с UserModel)

    Args:
        session: Асинхронная сессия базы данных.

    Returns:
        RegisterService: Настроенный экземпляр сервиса регистрации.

    Raises:
        ServiceUnavailableException: Если не удается создать сервис.

    Example:
        ```python
        # Автоматическое внедрение через FastAPI
        @router.post("/register")
        async def register_user(
            register_service: RegisterServiceDep,
            new_user: RegistrationRequestSchema,
        ):
            return await register_service.create_user(new_user)
        ```
    """
    try:
        logger.debug("Создание экземпляра RegisterService")
        return RegisterService(session=session)
    except Exception as e:
        logger.error(
            "Ошибка при создании RegisterService: %s", str(e), exc_info=True
        )
        raise


# Типизированная зависимость для удобства использования
RegisterServiceDep = Annotated[RegisterService, Depends(get_register_service)]
