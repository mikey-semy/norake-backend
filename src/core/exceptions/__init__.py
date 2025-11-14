from .base import BaseAPIException
from .common import (BadRequestError, ConflictError, ForbiddenError,
                     NotFoundError)
from .dependencies import ServiceUnavailableException
from .handlers import register_exception_handlers
from .health import ServiceUnavailableError
from .rate_limits import RateLimitExceededError
from .auth import (AuthenticationError, InvalidCredentialsError,
                   InvalidEmailFormatError, InvalidPasswordError,
                   InvalidCurrentPasswordError, WeakPasswordError,
                   TokenError, TokenMissingError, TokenExpiredError,
                   TokenInvalidError, InvalidUserDataError)
from .users import (UserNotFoundError, UserExistsError, UserCreationError,
                    UserInactiveError)
from .register import (UserAlreadyExistsError, RoleAssignmentError)
from .issues import (IssueNotFoundError, IssueAlreadyResolvedError,
                     IssuePermissionDeniedError, IssueValidationError)
from .issue_comments import (CommentNotFoundError, CommentAccessDeniedError)
from .templates import (TemplateNotFoundError, TemplatePermissionDeniedError,
                        TemplateValidationError, TemplateInactiveError)
from .openrouter import (OpenRouterError, OpenRouterConfigError)
from .knowledge_bases import (KnowledgeBaseNotFoundError, DocumentNotFoundError)
from .search import (SearchError, SearchTimeoutError)
from .document_services import (
    DocumentServiceNotFoundError,
    DocumentServicePermissionDeniedError,
    DocumentServiceValidationError,
    DocumentUploadError,
    ThumbnailGenerationError,
    QRCodeGenerationError,
    FunctionNotAvailableError,
    DocumentAccessDeniedError,
    FileTypeValidationError,
    FileSizeExceededError,
)

__all__ = [
    # Base
    "BaseAPIException",

    # Rate Limits
    "RateLimitExceededError",

    # Common
    "NotFoundError",
    "BadRequestError",
    "ConflictError",
    "ForbiddenError",

    # Dependencies
    "ServiceUnavailableException",

    # Health
    "ServiceUnavailableError",

    # Handlers
    "register_exception_handlers",

    # Auth
    "AuthenticationError",
    "InvalidCredentialsError",
    "InvalidEmailFormatError",
    "InvalidPasswordError",
    "InvalidCurrentPasswordError",
    "WeakPasswordError",
    "TokenError",
    "TokenMissingError",
    "TokenExpiredError",
    "TokenInvalidError",
    "InvalidUserDataError",

    # Users
    "UserNotFoundError",
    "UserExistsError",
    "UserCreationError",
    "UserInactiveError",

    # Registration
    "UserAlreadyExistsError",
    "RoleAssignmentError",

    # Issues
    "IssueNotFoundError",
    "IssueAlreadyResolvedError",
    "IssuePermissionDeniedError",
    "IssueValidationError",

    # Issue Comments
    "CommentNotFoundError",
    "CommentAccessDeniedError",

    # Templates
    "TemplateNotFoundError",
    "TemplatePermissionDeniedError",
    "TemplateValidationError",
    "TemplateInactiveError",

    # OpenRouter
    "OpenRouterError",
    "OpenRouterConfigError",

    # Knowledge Bases
    "KnowledgeBaseNotFoundError",
    "DocumentNotFoundError",

    # Search
    "SearchError",
    "SearchTimeoutError",

    # Document Services
    "DocumentServiceNotFoundError",
    "DocumentServicePermissionDeniedError",
    "DocumentServiceValidationError",
    "DocumentUploadError",
    "ThumbnailGenerationError",
    "QRCodeGenerationError",
    "FunctionNotAvailableError",
    "DocumentAccessDeniedError",
    "FileTypeValidationError",
    "FileSizeExceededError",
]
