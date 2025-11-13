"""
Роутеры для работы с комментариями к проблемам.

Модуль предоставляет HTTP API для управления комментариями, разделённое на:
- IssueCommentPublicRouter (BaseRouter) - публичные GET endpoints
- IssueCommentProtectedRouter (ProtectedRouter) - защищённые POST/DELETE endpoints

Обработка исключений: автоматическая обработка через глобальный exception handler.
Роутеры преобразуют domain objects (IssueCommentModel) в Pydantic схемы для ответа.
"""

from uuid import UUID

from fastapi import status

from src.core.dependencies.issue_comments import IssueCommentServiceDep
from src.core.security import CurrentUserDep
from src.routers.base import BaseRouter, ProtectedRouter
from src.schemas.v1.issue_comments import (
    CommentCreateRequestSchema,
    CommentDetailSchema,
    CommentListResponseSchema,
    CommentResponseSchema,
)


class IssueCommentPublicRouter(BaseRouter):
    """
    Публичный роутер для чтения комментариев к проблемам.

    Предоставляет HTTP API для просмотра комментариев:

    Public Endpoints (без аутентификации):
        GET /issues/{issue_id}/comments - Список комментариев проблемы

    Архитектурные особенности:
        - Endpoints публичные для чтения истории обсуждений
        - Роутер преобразует IssueCommentModel → Schema
        - Бизнес-логика в IssueCommentService
    """

    def __init__(self):
        """Инициализирует IssueCommentPublicRouter с префиксом и тегами."""
        super().__init__(prefix="issues", tags=["Issue Comments"])

    def configure(self):
        """Настройка публичных endpoint'ов роутера."""

        # ==================== LIST ====================

        @self.router.get(
            path="/{issue_id}/comments",
            response_model=CommentListResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 💬 Получить список комментариев проблемы

            Возвращает все комментарии для указанной проблемы,
            отсортированные по дате создания (от старых к новым).

            ### 🌐 Публичный доступ (без токена)

            ### Path параметры:
            * **issue_id**: UUID проблемы

            ### Returns:
            * **CommentListResponseSchema**: Список комментариев с информацией об авторах

            ### Примеры использования:
            ```bash
            # Получить все комментарии проблемы
            curl -X GET "http://localhost:8000/api/v1/issues/{issue_id}/comments"
            ```

            ### Ответ:
            ```json
            {
              "success": true,
              "message": "Комментарии получены успешно",
              "data": [
                {
                  "id": "uuid",
                  "issue_id": "uuid",
                  "author": {
                    "id": "uuid",
                    "username": "john_doe",
                    "email": "john@example.com"
                  },
                  "content": "Попробуйте перезагрузить сервер",
                  "is_solution": false,
                  "created_at": "2025-11-11T10:00:00Z",
                  "updated_at": "2025-11-11T10:00:00Z"
                }
              ]
            }
            ```

            ### Ошибки:
            * **404**: Проблема не найдена
            """,
            summary="📄 Список комментариев проблемы",
        )
        async def get_comments(
            issue_id: UUID,
            service: IssueCommentServiceDep = None,
        ) -> CommentListResponseSchema:
            """Получение списка комментариев для проблемы."""
            # Бизнес-логика: получение комментариев
            comments = await service.get_comments(issue_id=issue_id)

            # Преобразование domain objects → schemas
            comments_data = [
                CommentDetailSchema.model_validate(comment)
                for comment in comments
            ]

            return CommentListResponseSchema(
                success=True,
                message="Комментарии получены успешно",
                data=comments_data,
            )


class IssueCommentProtectedRouter(ProtectedRouter):
    """
    Защищённый роутер для управления комментариями к проблемам.

    Предоставляет HTTP API для создания и удаления комментариев:

    Protected Endpoints (требуется аутентификация):
        POST /issues/{issue_id}/comments - Создать комментарий
        DELETE /issues/{issue_id}/comments/{comment_id} - Удалить комментарий

    Архитектурные особенности:
        - Все endpoints требуют аутентификации (CurrentUserDep)
        - Роутер преобразует IssueCommentModel → Schema
        - Бизнес-логика и проверка прав в IssueCommentService
    """

    def __init__(self):
        """Инициализирует IssueCommentProtectedRouter с префиксом и тегами."""
        super().__init__(prefix="issues", tags=["Issue Comments"])

    def configure(self):
        """Настройка защищённых endpoint'ов роутера."""

        # ==================== CREATE ====================

        @self.router.post(
            path="/{issue_id}/comments",
            response_model=CommentResponseSchema,
            status_code=status.HTTP_201_CREATED,
            description="""
            ## ➕ Создать новый комментарий к проблеме

            Создаёт комментарий для указанной проблемы от имени текущего пользователя.

            ### 🔒 Требуется аутентификация

            ### Path параметры:
            * **issue_id**: UUID проблемы

            ### Body параметры:
            * **content**: Текстовое содержимое комментария (1-5000 символов)
            * **is_solution**: Флаг, отмечающий комментарий как решение (опционально, по умолчанию false)

            ### Returns:
            * **CommentResponseSchema**: Созданный комментарий с полной информацией

            ### Примеры использования:
            ```bash
            # Создать обычный комментарий
            curl -X POST "http://localhost:8000/api/v1/issues/{issue_id}/comments" \\
              -H "Authorization: Bearer <token>" \\
              -H "Content-Type: application/json" \\
              -d '{
                "content": "Попробуйте перезагрузить сервер и проверить логи"
              }'

            # Создать комментарий-решение
            curl -X POST "http://localhost:8000/api/v1/issues/{issue_id}/comments" \\
              -H "Authorization: Bearer <token>" \\
              -H "Content-Type: application/json" \\
              -d '{
                "content": "Проблема решена после обновления драйвера",
                "is_solution": true
              }'
            ```

            ### Ответ:
            ```json
            {
              "success": true,
              "message": "Комментарий создан успешно",
              "data": {
                "id": "uuid",
                "issue_id": "uuid",
                "author": {
                  "id": "uuid",
                  "username": "john_doe",
                  "email": "john@example.com"
                },
                "content": "Попробуйте перезагрузить сервер",
                "is_solution": false,
                "created_at": "2025-11-11T10:00:00Z",
                "updated_at": "2025-11-11T10:00:00Z"
              }
            }
            ```

            ### Ошибки:
            * **401**: Не авторизован
            * **404**: Проблема не найдена
            * **422**: Валидация не пройдена (некорректный content)
            """,
            summary="➕ Создать комментарий",
        )
        async def create_comment(
            issue_id: UUID,
            request: CommentCreateRequestSchema,
            current_user: CurrentUserDep = None,
            service: IssueCommentServiceDep = None,
        ) -> CommentResponseSchema:
            """Создание нового комментария к проблеме."""
            # Бизнес-логика: создание комментария
            comment = await service.create_comment(
                issue_id=issue_id,
                author_id=current_user.id,
                content=request.content,
                is_solution=request.is_solution,
            )

            # Преобразование domain object → schema
            comment_data = CommentDetailSchema.model_validate(comment)

            return CommentResponseSchema(
                success=True,
                message="Комментарий создан успешно",
                data=comment_data,
            )

        # ==================== DELETE ====================

        @self.router.delete(
            path="/{issue_id}/comments/{comment_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            description="""
            ## 🗑️ Удалить комментарий

            Удаляет комментарий. Только автор комментария или администратор могут удалить комментарий.

            ### 🔒 Требуется аутентификация

            ### Path параметры:
            * **issue_id**: UUID проблемы (для REST-структуры URL)
            * **comment_id**: UUID комментария для удаления

            ### Returns:
            * **204 No Content**: Комментарий успешно удалён

            ### Примеры использования:
            ```bash
            # Удалить комментарий
            curl -X DELETE "http://localhost:8000/api/v1/issues/{issue_id}/comments/{comment_id}" \\
              -H "Authorization: Bearer <token>"
            ```

            ### Ошибки:
            * **401**: Не авторизован
            * **403**: Нет прав для удаления (не автор и не админ)
            * **404**: Комментарий не найден
            """,
            summary="🗑️ Удалить комментарий",
        )
        async def delete_comment(
            _issue_id: UUID,  # Для REST-структуры URL (не используется в логике)
            comment_id: UUID,
            current_user: CurrentUserDep = None,
            service: IssueCommentServiceDep = None,
        ) -> None:
            """Удаление комментария (только автор или admin)."""
            # Проверка роли администратора
            is_admin = current_user.has_role("admin")

            # Бизнес-логика: удаление комментария с проверкой прав
            await service.delete_comment(
                comment_id=comment_id,
                user_id=current_user.id,
                is_admin=is_admin,
            )

            # 204 No Content - ничего не возвращаем
            return None
