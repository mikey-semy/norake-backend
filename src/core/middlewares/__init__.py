from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from src.core.settings import settings

from .logging import LoggingMiddleware


def setup_middlewares(app: FastAPI):
    """
    Настраивает все middleware для приложения FastAPI.
    """
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(SessionMiddleware, secret_key=settings.TOKEN_SECRET_KEY)
    app.add_middleware(CORSMiddleware, **settings.cors_params)
