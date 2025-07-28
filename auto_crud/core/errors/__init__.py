"""
Custom exception classes for FastAPI-AutoCRUD.

This module defines the exception hierarchy used throughout FastAPI-AutoCRUD
for consistent error handling and meaningful error messages.
"""


class AutoCRUDException(Exception):
    """
    Base exception class for all FastAPI-AutoCRUD errors.

    This is the parent class for all custom exceptions in FastAPI-AutoCRUD.
    It provides a common base for error handling and allows catching
    all FastAPI-AutoCRUD-specific exceptions with a single except clause.

    Example:
        ```python
        try:
            user = await crud.get_by_id(db, user_id)
        except AutoCRUDException as e:
            # Handle any FastAPI-AutoCRUD error
            logger.error(f"AutoCRUD error: {e}")
        ```
    """

    pass


class ValidationError(AutoCRUDException):
    """
    Raised when data validation fails.

    This exception is raised when input data fails validation,
    such as invalid email formats, missing required fields,
    or business rule violations.

    Example:
        ```python
        if not is_valid_email(user_data.email):
            raise ValidationError("Invalid email format")

        if len(user_data.name) < 2:
            raise ValidationError("Name must be at least 2 characters")
        ```
    """

    pass


class NotFoundError(AutoCRUDException):
    """
    Raised when a requested resource is not found.

    This exception is raised when attempting to retrieve,
    update, or delete a resource that doesn't exist.

    Example:
        ```python
        user = await db.execute(select(User).where(User.id == user_id))
        user = user.scalar_one_or_none()

        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")
        ```
    """

    pass


class PermissionError(AutoCRUDException):
    """
    Raised when access is denied due to insufficient permissions.

    This exception is raised when a user attempts to perform
    an operation they don't have permission for, such as
    updating another user's profile or deleting admin accounts.

    Example:
        ```python
        if current_user.role != "admin" and current_user.id != user_id:
            raise PermissionError("Cannot update other user's profile")

        if user.role == "admin":
            raise PermissionError("Cannot delete admin users")
        ```
    """

    pass


class ConfigurationError(AutoCRUDException):
    """
    Raised when there are configuration issues.

    This exception is raised when required configuration is missing
    or invalid, such as missing database URLs, invalid model
    configurations, or missing dependencies.

    Example:
        ```python
        if not model:
            raise ConfigurationError("Model is required")

        if not session_factory:
            raise ConfigurationError("Session factory is required")
        ```
    """

    pass


class FilterError(AutoCRUDException):
    """
    Raised when filtering operations fail.

    This exception is raised when there are issues with query
    filters, such as invalid operators, non-existent fields,
    or type mismatches in filter values.

    Example:
        ```python
        valid_operators = ["eq", "ne", "gt", "gte", "lt", "lte"]

        if operator not in valid_operators:
            raise FilterError(f"Invalid operator '{operator}'")

        if not hasattr(User, field):
            raise FilterError(f"Invalid field '{field}' for User model")
        ```
    """

    pass
