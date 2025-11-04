from fastapi import FastAPI

from .main import MainRouter
from .v1 import APIv1


def setup_routers(app: FastAPI):
    """
    Настраивает все роутеры для приложения FastAPI.
    """
    app.include_router(MainRouter().get_router())
    app.include_router(APIv1().get_router(), prefix="/api/v1")
