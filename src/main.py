"""Main FastAPI application."""

from fastapi import FastAPI


import src.core.lifespan.admin_init_handler  # noqa: F401
import src.core.lifespan.database   # noqa: F401
import src.core.lifespan.cache   # noqa: F401
import src.core.lifespan.fixtures  # noqa: F401
# import src.core.lifespan.messaging   # noqa: F401

from src.core.exceptions import register_exception_handlers
from src.core.logging import setup_logging
from src.core.middlewares import setup_middlewares
from src.core.settings import settings
from src.routers import setup_routers


def create_application() -> FastAPI:
    """
    Создает и настраивает экземпляр приложения FastAPI.

    Эта функция инициализирует приложение, настраивает логирование,
    регистрирует обработчики исключений, подключает middleware и роуты.

    Returns:
        FastAPI: Настроенный экземпляр приложения FastAPI.
    """
    app = FastAPI(**settings.app_params)
    setup_logging()
    register_exception_handlers(app=app)
    setup_middlewares(app)
    setup_routers(app)

    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, **settings.uvicorn_params)
