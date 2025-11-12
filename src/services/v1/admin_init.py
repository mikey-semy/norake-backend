"""
🎯 МОДУЛЬ: AdminInitService - Инициализация дефолтного администратора
=======================================================================

📋 НАЗНАЧЕНИЕ МОДУЛЯ:
    Автоматическое создание дефолтного администратора при первом запуске приложения.
    Использует данные из переменных окружения (ENV) для настройки учётных данных.

🏗️ АРХИТЕКТУРНЫЕ ПРИНЦИПЫ:
    ✅ BaseService Pattern: Наследование от BaseService
    ✅ Environment-driven: Все параметры из ENV переменных
    ✅ Idempotency: Безопасное повторное выполнение (проверка существования)
    ✅ Security: Безопасное хеширование паролей через PasswordManager
    ✅ Logging: Детальное логирование процесса создания

🔧 ФУНКЦИОНАЛЬНОСТЬ:
    • Проверка существования админа по username
    • Создание нового админа с данными из settings
    • Хеширование пароля через PasswordManager
    • Безопасное логирование (пароли не логируются)

📊 ИСПОЛЬЗУЕМЫЕ МОДЕЛИ:
    • UserModel - модель пользователя/админа в БД
    • UserCreateSchema - схема для создания пользователя

⚡ АВТОМАТИЧЕСКИЙ ЗАПУСК:
    Вызывается при старте приложения через lifespan manager
    Если админ с таким username уже есть - пропускается

🛡️ БЕЗОПАСНОСТЬ:
    • Пароли хешируются Argon2 перед сохранением
    • Пароли не логируются в открытом виде
    • Использование SecretStr для ENV переменных
"""
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import PasswordManager
from src.repository.v1.users import UserRepository
from src.models.v1.users import UserModel
from src.models.v1.roles import RoleCode
from src.services.base import BaseService


class AdminInitService(BaseService):
    """
    Сервис инициализации дефолтного администратора.

    Создаёт админа из ENV переменных при первом запуске.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализация сервиса.

        Args:
            session (AsyncSession): Асинхронная сессия БД
        """
        super().__init__(session=session)
        self.repository = UserRepository(session=session, model=UserModel)
        self.password_manager = PasswordManager()

    async def create_default_admin_if_not_exists(self) -> None:
        """
        Создаёт дефолтного админа и дополнительных админов, если они не существуют.

        Процесс:
        1. Создаёт дефолтного админа из DEFAULT_ADMIN_* переменных
        2. Создаёт дополнительных админов из ADMINS переменной
        3. Для каждого админа:
           - Проверяет существование по username
           - Хеширует пароль через PasswordManager
           - Сохраняет в БД через UserRepository

        Raises:
            Любые исключения логируются и пробрасываются дальше
        """
        try:
            # 1. Создаём дефолтного админа
            await self._create_admin(
                username=self.settings.DEFAULT_ADMIN_USERNAME,
                email=self.settings.DEFAULT_ADMIN_EMAIL,
                password=self.settings.DEFAULT_ADMIN_PASSWORD.get_secret_value(),
                is_default=True
            )

            # 2. Создаём дополнительных админов из ENV
            additional_admins = self.settings.additional_admins
            if additional_admins:
                self.logger.info(
                    "📋 Найдено %d дополнительных администраторов в ENV",
                    len(additional_admins)
                )
                for admin_data in additional_admins:
                    await self._create_admin(
                        username=admin_data["username"],
                        email=admin_data["email"],
                        password=admin_data["password"],
                        is_default=False
                    )

        except Exception as e:
            self.logger.error(
                "❌ Ошибка создания администраторов: %s",
                e,
                exc_info=True
            )
            raise

    async def _create_admin(
        self,
        username: str,
        email: str,
        password: str,
        is_default: bool = False
    ) -> None:
        """
        Создаёт одного администратора, если он не существует.

        Args:
            username (str): Имя пользователя
            email (str): Email
            password (str): Пароль в открытом виде
            is_default (bool): Является ли это дефолтным админом

        Raises:
            Любые исключения пробрасываются дальше
        """
        # Проверяем существование по username
        existing_admin = await self.repository.get_item_by_field(
            "username", username
        )

        if existing_admin:
            admin_type = "дефолтный" if is_default else "дополнительный"
            self.logger.info(
                "✅ %s админ '%s' уже существует - пропускаем создание",
                admin_type.capitalize(), username
            )
            return

        # Хешируем пароль
        hashed_password = self.password_manager.hash_password(password)

        # Создаём админа через create_user_with_role (как в RegisterService)
        admin_data = {
            "username": username,
            "email": email,
            "password_hash": hashed_password,
            "is_active": True,  # Админ активен сразу
        }

        # ВАЖНО: Роль присваивается через create_user_with_role,
        # не через прямое присвоение - role это relationship!
        await self.repository.create_user_with_role(
            user_data=admin_data,
            role_code=RoleCode.ADMIN.value,  # "admin" string
        )

        admin_type = "дефолтный" if is_default else "дополнительный"
        self.logger.info(
            "✅ Создан %s админ: username='%s', email='%s'",
            admin_type, username, email
        )
