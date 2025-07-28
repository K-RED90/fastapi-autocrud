# FastAPI-AutoCRUD

A powerful, enterprise-level FastAPI CRUD router factory for SQLAlchemy models. It automatically generates REST endpoints with advanced features: filtering, pagination, searching, sorting, bulk operations, custom endpoint decorators, and lifecycle hooks.

---

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts & Features](#core-concepts--features)
- [Endpoint Reference](#endpoint-reference)
- [Advanced Usage](#advanced-usage)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Overview

**FastAPI-AutoCRUD** eliminates boilerplate for CRUD APIs. It:
- Generates all CRUD endpoints for your SQLAlchemy models
- Supports advanced filtering, pagination, search, sorting, and bulk operations
- Lets you add custom endpoints and business logic with hooks and decorators
- Automatically generates Pydantic response models if you don't provide them

---

## Installation

```bash
pip install FastAPI-AutoCRUD
```

**Requirements:**
- Python 3.12+
- FastAPI 0.115.14+
- SQLAlchemy 2.0.41+
- Pydantic 2.11.7+

---

## Quick Start

### 1. Define Your SQLAlchemy Model (2.0 style)

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    # ... other fields ...
```

**Why this matters:** Using `Mapped` and `mapped_column` ensures full SQLAlchemy 2.0 compatibility and type safety.

### 2. Create Pydantic Schemas

```python
from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    username: str
    email: EmailStr

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
```

### 3. Set Up Async Database Session

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

DATABASE_URL = "postgresql+asyncpg://user:password@localhost/dbname"
engine = create_async_engine(DATABASE_URL)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
```

### 4. Create CRUD and Router

```python
from auto_crud.core.crud.base import BaseCRUD
from auto_crud.core.crud.router import RouterFactory

user_crud = BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User)
user_router_factory = RouterFactory(
    crud=user_crud,
    session_factory=get_session,
    create_schema=UserCreate,
    update_schema=UserUpdate,
    prefix="/users",
    tags=["users"],
    enable_pagination=True,
    enable_search=True,
    enable_sorting=True,
    enable_filters=True,
    search_fields=["username", "email"],
    sort_fields=["username", "email"],
    page_size=20,
    max_page_size=100,
)
user_router = user_router_factory.get_router()
```

### 5. Register the Router in FastAPI

```python
from fastapi import FastAPI
app = FastAPI()
app.include_router(user_router, prefix="/api/v1")
```

---

## Core Concepts & Features

### 1. CRUD Endpoints (Auto-Generated)

**All endpoints are generated for you:**
- `POST   /users/`         — Create
- `GET    /users/`         — List (with pagination, filtering, search, sorting)
- `GET    /users/{id}`     — Read by ID
- `PUT    /users/{id}`     — Update
- `PATCH  /users/{id}`     — Partial update
- `DELETE /users/{id}`     — Delete
- `POST   /users/bulk`     — Bulk create
- `PUT    /users/bulk`     — Bulk update
- `DELETE /users/bulk`     — Bulk delete

**Explanation:**
- **No need to write these endpoints yourself.** The router factory automatically generates all standard CRUD operations.
- **Bulk endpoints** accept lists of objects (for create/update) or IDs (for delete) for efficient batch operations.
- **All endpoints support dependency injection** for authentication, authorization, and other middleware.
- **HTTP methods are properly mapped:** PUT for full updates, PATCH for partial updates.

### 2. Automatic Pydantic Response Models

If you do **not** provide a response model for an operation, FastAPI-AutoCRUD will **dynamically generate** a Pydantic model from your SQLAlchemy model's columns. This ensures:
- All fields are included
- Types are inferred from your model
- Nullability and defaults are respected

**Best Practice:** For custom serialization or hiding fields, provide your own response model.

### 3. Advanced Filtering System

FastAPI-AutoCRUD provides a sophisticated filtering system with multiple operators and logical combinations.

**Supported Operators:**
- **Comparison:** `eq`, `ne`, `gt`, `ge`, `lt`, `le`
- **Text Search:** `like`, `ilike`, `contains`, `startswith`, `endswith`
- **Collections:** `in`, `not_in`
- **Null Handling:** `is_null`, `is_not_null`
- **Ranges:** `between`
- **Logical:** `and`, `or`, `not`

**Client Usage Examples:**
```
GET /users?filters=status__eq=active
GET /users?filters=age__gte=18,status__in=active,pending
GET /users?filters=created_at__between=2024-01-01,2024-01-31
GET /users?filters=name__ilike=%john%,email__contains=gmail
GET /users?filters=and(field1__eq=value1,field2__gt=10)
```

**Configuration:**
```python
user_router_factory = RouterFactory(
    ...,
    enable_filters=True,
    filter_spec={
        "username": ("eq", "contains", "startswith"),
        "email": ("eq", "ilike"),
        "age": ("eq", "gt", "ge", "lt", "le", "between"),
        "status": ("eq", "in", "not_in"),
    },
)
```

**Explanation:**
- **Security:** Use `filter_spec` to whitelist allowed fields and operators, preventing exposure of sensitive data.
- **Performance:** Restricting operators helps optimize database queries.
- **Flexibility:** Support for complex logical expressions with `and`, `or`, `not` operators.

### 4. Pagination

Pagination is enabled by default and provides comprehensive metadata.

**Query Parameters:**
- `page`: Page number (1-based)
- `size`: Items per page (1-100, configurable)

**Response Structure:**
```json
{
  "items": [...],
  "total": 150,
  "page": 2,
  "size": 20,
  "pages": 8,
  "has_next": true,
  "has_prev": true
}
```

**Configuration:**
```python
user_router_factory = RouterFactory(
    ...,
    enable_pagination=True,
    page_size=20,
    max_page_size=100,
)
```

**Explanation:**
- **Consistent API:** All list endpoints return the same pagination structure.
- **Performance:** Limits result sets to prevent memory issues.
- **Metadata:** Provides all necessary information for building pagination UI.

### 5. Global Search

Global search allows searching across multiple fields simultaneously.

**Configuration:**
```python
user_router_factory = RouterFactory(
    ...,
    enable_search=True,
    search_fields=["username", "email", "full_name"],
)
```

**Client Usage:**
```
GET /users?search=john
```

**Explanation:**
- **Multi-field:** Searches across all specified fields using case-insensitive LIKE queries.
- **Simple Interface:** Single search parameter for complex queries.
- **Performance:** Uses database indexes for efficient searching.

### 6. Sorting

Multi-field sorting with configurable fields and directions.

**Configuration:**
```python
user_router_factory = RouterFactory(
    ...,
    enable_sorting=True,
    sort_fields=["username", "email", "created_at"],
    sort_default="created_at",
)
```

**Client Usage:**
```
GET /users?sort_by=username,-created_at
```

**Explanation:**
- **Multi-field:** Sort by multiple fields in order.
- **Direction:** Prefix with `-` for descending order.
- **Default:** Falls back to `sort_default` if no sorting specified.

### 7. Bulk Operations

Efficient batch operations for creating, updating, and deleting multiple records.

**Endpoints:**
- `POST /users/bulk` — Bulk create
- `PUT /users/bulk` — Bulk update  
- `DELETE /users/bulk` — Bulk delete

**Bulk Create Example:**
```json
POST /users/bulk
[
  {"username": "user1", "email": "user1@example.com"},
  {"username": "user2", "email": "user2@example.com"}
]
```

**Bulk Update Example:**
```json
PUT /users/bulk
[
  {"id": "uuid1", "username": "updated1"},
  {"id": "uuid2", "email": "updated2@example.com"}
]
```

**Bulk Delete Example:**
```json
DELETE /users/bulk
["uuid1", "uuid2", "uuid3"]
```

**Response Structure:**
```json
{
  "created": 2,
  "updated": 3,
  "deleted": 1,
  "items": [...],
  "errors": [...]
}
```

**Explanation:**
- **Performance:** Batch operations are much faster than individual requests.
- **Transaction Safety:** All operations within a bulk request are atomic.
- **Error Handling:** Partial failures are reported with detailed error information.

### 8. Prefetching (Eager Loading)

Use the `prefetch` parameter to specify relationships to eager load for performance.

**Configuration:**
```python
user_router_factory = RouterFactory(
    ...,
    prefetch=["posts", "profile"],
)
```

**Explanation:**
- **N+1 Problem:** Prevents the common N+1 query problem when accessing related data.
- **Performance:** Reduces database round trips significantly.
- **Flexibility:** Can be set globally or per-request.

### 9. Custom Actions

Use the `@action` decorator to add custom endpoints to your router factory class.

**Example:**
```python
from auto_crud.core.crud.decorators import action

class UserRouterFactory(RouterFactory[User, uuid.UUID, UserCreate, UserUpdate]):
    @action(method="GET", detail=False, url_path="verified")
    async def get_verified_users(self, session: AsyncSession):
        filters = [
            FilterParam(field="is_verified", operator="eq", value=True)
        ]
        return await self.crud.list_objects(session, filters=filters)

user_router_factory = UserRouterFactory(
    crud=user_crud,
    session_factory=get_session,
    create_schema=UserCreate,
    update_schema=UserUpdate,
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_auth)],
    enable_pagination=True,
    enable_search=True,
    enable_sorting=True,
    enable_filters=True,
    search_fields=["username", "email", "full_name"],
    sort_fields=["username", "email", "created_at"],
    sort_default="created_at",
    page_size=20,
    max_page_size=100,
    prefetch=["profile", "posts"],
    filter_spec={
        "username": ("eq", "contains", "startswith"),
        "email": ("eq", "ilike"),
        "status": ("eq", "in"),
        "created_at": ("eq", "gt", "ge", "lt", "le", "between"),
    },
    response_schemas={
        "create": UserResponse,
        "update": UserResponse,
        "read": UserResponse,
        "list": UserResponse,
    },
)

# 4. Get router and register
user_router = user_router_factory.get_router()
app.include_router(user_router, prefix="/api/v1")
```

---

**For more examples, see the `sample/` directory.**

---

## License
MIT