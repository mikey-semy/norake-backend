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
from .register import (UserCreationError, UserAlreadyExistsError,
                       RoleAssignmentError)
from .issues import (IssueNotFoundError, IssueAlreadyResolvedError,
                     IssuePermissionDeniedError, IssueValidationError)

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
    "UserCreationError",
    "UserAlreadyExistsError",
    "RoleAssignmentError",
    
    # Issues
    "IssueNotFoundError",
    "IssueAlreadyResolvedError",
    "IssuePermissionDeniedError",
    "IssueValidationError",
]

