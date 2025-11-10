"""
Зависимости для сервиса шаблонов (Templates).

Этот модуль содержит провайдер (фабрику) для создания экземпляра сервиса
шаблонов с автоматическим внедрением зависимостей через FastAPI Depends.

Providers:
    - get_template_service: Провайдер для TemplateService

Typed Dependencies:
    - TemplateServiceDep: Типизированная зависимость для TemplateService

Usage:
    ```python
    from src.core.dependencies import TemplateServiceDep

    @router.post("/templates")
    async def create_template(
        template_service: TemplateServiceDep = None,
        data: TemplateCreateRequestSchema = ...,
    ) -> TemplateResponseSchema:
        template = await template_service.create_template(...)
        return TemplateResponseSchema(success=True, data=template)
    ```
"""

import logging
from typing import Annotated

from fastapi import Depends

from src.core.dependencies.database import AsyncSessionDep
from src.services.v1.templates import TemplateService

logger = logging.getLogger(__name__)


async def get_template_service(
    session: AsyncSessionDep,
) -> TemplateService:
    """
    Провайдер для TemplateService.

    Создаёт экземпляр TemplateService с внедрёнными зависимостями:
    - Сессия базы данных (для работы с TemplateModel)

    Args:
        session: Асинхронная сессия базы данных.

    Returns:
        TemplateService: Готовый к использованию сервис шаблонов.

    Example:
        ```python
        async def endpoint(service: TemplateServiceDep = None):
            templates = await service.get_active_templates()
            return templates
        ```
    """
    logger.debug("Создание экземпляра TemplateService")
    return TemplateService(session=session)


# Типизированная зависимость для использования в роутерах
# = None ОБЯЗАТЕЛЬНО для корректной работы FastAPI Depends!
TemplateServiceDep = Annotated[TemplateService, Depends(get_template_service)]
