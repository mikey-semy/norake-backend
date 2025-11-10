"""
Схемы API версии 1.

Этот пакет объединяет все схемы для API v1.

Модули:
    auth: Схемы аутентификации
    health: Схемы health-check
    issues: Схемы проблем (Issues)
    register: Схемы регистрации
    templates: Схемы шаблонов (Templates)
"""

from .auth import *  # noqa: F401, F403
from .health import *  # noqa: F401, F403
from .issues import *  # noqa: F401, F403
from .register import *  # noqa: F401, F403
from .templates import *  # noqa: F401, F403
