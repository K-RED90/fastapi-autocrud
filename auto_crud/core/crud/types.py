"""
Type definitions for FastAPI-AutoCRUD.

This module contains the core type variables used throughout FastAPI-AutoCRUD
for type-safe generic programming.
"""

from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase

# Type variable for SQLAlchemy model classes
ModelType = TypeVar("ModelType", bound=DeclarativeBase)
"""
Type variable for SQLAlchemy model classes.

This type variable is bound to DeclarativeBase, ensuring that only
SQLAlchemy model classes can be used where this type is expected.

Example:
    ```python
    class UserCRUD(BaseCRUD[User, int, UserCreate, UserUpdate]):
        # User is a SQLAlchemy model class
        pass
    ```
"""

# Type variable for Pydantic create schemas
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
"""
Type variable for Pydantic create schemas.

This type variable is bound to BaseModel, ensuring that only
Pydantic models can be used for create operations.

Example:
    ```python
    class UserCreate(BaseModel):
        email: str
        name: str
    
    class UserCRUD(BaseCRUD[User, int, UserCreate, UserUpdate]):
        # UserCreate is a Pydantic model for creation
        pass
    ```
"""

# Type variable for Pydantic update schemas
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
"""
Type variable for Pydantic update schemas.

This type variable is bound to BaseModel, ensuring that only
Pydantic models can be used for update operations.

Example:
    ```python
    class UserUpdate(BaseModel):
        email: Optional[str] = None
        name: Optional[str] = None
    
    class UserCRUD(BaseCRUD[User, int, UserCreate, UserUpdate]):
        # UserUpdate is a Pydantic model for updates
        pass
    ```
"""

# Type variable for primary key types
PrimaryKeyType = TypeVar("PrimaryKeyType")
"""
Type variable for primary key types.

This type variable is not bound, allowing any type to be used
as a primary key (int, str, UUID, etc.).

Example:
    ```python
    class UserCRUD(BaseCRUD[User, int, UserCreate, UserUpdate]):
        # int is the primary key type
        pass
    
    class UUIDUserCRUD(BaseCRUD[User, UUID, UserCreate, UserUpdate]):
        # UUID is the primary key type
        pass
    ```
"""
