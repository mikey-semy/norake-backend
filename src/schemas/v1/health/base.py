"""
Базовые схемы для health check.

Содержит схемы данных для проверки состояния приложения.
"""

from pydantic import Field

from src.schemas.base import CommonBaseSchema


class HealthCheckDataSchema(CommonBaseSchema):
    """
    Схема данных для health check.

    Attributes:
        app (str): Статус приложения
        db (str): Статус базы данных
    """

    app: str = Field(default="ok", description="Статус приложения", examples=["ok"])
    db: str = Field(
        default="ok",
        description="Статус базы данных",
        examples=["ok", "fail", "unknown"],
    )
