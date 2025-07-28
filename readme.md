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
- [License](#license)
- [Contributing](/CONTRIBUTING.md)

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
- SQLAlchemy 2.0.41+ (with async support via greenlet)
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
    sort_default="-created_at", # sort by created_at in descending order
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

### 3.1. FilterParam Class - Server Side Filtering

The `FilterParam` class is the core component of FastAPI-AutoCRUD's filtering system. It provides a type-safe, flexible way to build complex database queries programmatically.

#### FilterParam Structure

```python
from auto_crud.core.schemas.pagination import FilterParam

# Basic filter
filter_param = FilterParam(
    field="username",
    operator="eq",
    value="john_doe"
)

```

#### Supported Operators by Data Type

**String Fields:**
```python
# Exact match
FilterParam(field="username", operator="eq", value="john")

# Case-insensitive search
FilterParam(field="email", operator="ilike", value="%gmail%")

# Pattern matching
FilterParam(field="name", operator="startswith", value="John")
FilterParam(field="description", operator="contains", value="important")

# Multiple values
FilterParam(field="status", operator="in", value=["active", "pending"])
```

**Numeric Fields:**
```python
# Comparisons
FilterParam(field="age", operator="gte", value=18)
FilterParam(field="price", operator="between", value=[10.0, 100.0])

# Range queries
FilterParam(field="score", operator="gt", value=80)
FilterParam(field="quantity", operator="le", value=100)
```

**DateTime Fields:**
```python
from datetime import datetime, date

# Date comparisons
FilterParam(field="created_at", operator="gte", value=date(2024, 1, 1))
FilterParam(field="updated_at", operator="between", value=[
    datetime(2024, 1, 1, 0, 0, 0),
    datetime(2024, 12, 31, 23, 59, 59)
])
```

**Boolean Fields:**
```python
# Boolean checks
FilterParam(field="is_active", operator="eq", value=True)
FilterParam(field="is_verified", operator="is_not_null", value=True)
```

**UUID Fields:**
```python
import uuid

# UUID comparisons
FilterParam(field="user_id", operator="eq", value=uuid.uuid4())
FilterParam(field="session_id", operator="in", value=[uuid1, uuid2, uuid3])
```

#### Logical Operators for Complex Queries

**AND Operator:**
```python
# Find users who are active AND over 18
and_filter = FilterParam(
    operator="and",
    value=[
        FilterParam(field="status", operator="eq", value="active"),
        FilterParam(field="age", operator="gte", value=18)
    ]
)
```

**OR Operator:**
```python
# Find users who are either admins OR verified
or_filter = FilterParam(
    operator="or",
    value=[
        FilterParam(field="role", operator="eq", value="admin"),
        FilterParam(field="is_verified", operator="eq", value=True)
    ]
)
```

**NOT Operator:**
```python
# Find users who are NOT inactive
not_filter = FilterParam(
    operator="not",
    value=[
        FilterParam(field="status", operator="eq", value="inactive")
    ]
)
```

#### Nested Relationships

FilterParam supports filtering on related models through dot notation:

```python
# Filter users by their profile information
FilterParam(field="profile.bio", operator="contains", value="developer")

# Filter posts by author information
FilterParam(field="author.username", operator="eq", value="john_doe")

# Filter orders by customer details
FilterParam(field="customer.address.city", operator="eq", value="New York")
```

#### Using FilterParam in Custom Endpoints

```python
from fastapi import Depends
from auto_crud.core.crud.decorators import action
from auto_crud.core.schemas.pagination import FilterParam

class UserRouterFactory(RouterFactory[User, uuid.UUID, UserCreate, UserUpdate]):
    
    @action(method="GET", detail=False, url_path="premium")
    async def get_premium_users(self, session: AsyncSession = Depends(get_session)):
        """Get all premium users with complex filtering."""
        
        filters = [
            FilterParam(field="subscription_type", operator="eq", value="premium"),
            FilterParam(
                operator="and",
                value=[
                    FilterParam(field="last_login", operator="gte", value=date(2024, 1, 1)),
                    FilterParam(field="is_active", operator="eq", value=True)
                ]
            )
        ]
        
        return await self.crud.list_objects(session, filters=filters)
    
    @action(method="GET", detail=False, url_path="search")
    async def search_users(self, q: str, session: AsyncSession = Depends(get_session)):
        """Custom search endpoint with multiple field matching."""
        
        filters = [
            FilterParam(
                operator="or",
                value=[
                    FilterParam(field="username", operator="ilike", value=f"%{q}%"),
                    FilterParam(field="email", operator="ilike", value=f"%{q}%"),
                    FilterParam(field="full_name", operator="ilike", value=f"%{q}%")
                ]
            )
        ]
        
        return await self.crud.list_objects(session, filters=filters)
```

#### Advanced Filtering Patterns

**Date Range Queries:**
```python
from datetime import datetime, timedelta

# Last 30 days
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

date_filter = FilterParam(
    field="created_at",
    operator="between",
    value=[start_date, end_date]
)
```

**Multi-level Nested Filters:**
```python
# Filter posts by author's profile information
nested_filter = FilterParam(
    field="author.profile.location.city",
    operator="eq",
    value="San Francisco"
)
```

**Complex Logical Combinations:**
```python
# Find active users who are either premium OR have high engagement
complex_filter = FilterParam(
    operator="and",
    value=[
        FilterParam(field="status", operator="eq", value="active"),
        FilterParam(
            operator="or",
            value=[
                FilterParam(field="subscription_type", operator="eq", value="premium"),
                FilterParam(field="engagement_score", operator="gte", value=80)
            ]
        )
    ]
)
```

#### Type Safety and Validation

FilterParam includes comprehensive type validation:

```python
# Automatic type casting
FilterParam(field="age", operator="eq", value="25")  # Automatically cast to int
FilterParam(field="is_active", operator="eq", value="true")  # Cast to bool
FilterParam(field="created_at", operator="eq", value="2024-01-01")  # Cast to date


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

Sorting with configurable field and direction.

**Configuration:**
```python
user_router_factory = RouterFactory(
    ...,
    enable_sorting=True,
    sort_default="-created_at", # sort by created_at in descending order
)
```

**Client Usage:**
```
GET /users?sort_by=-created_at
```

**Explanation:**
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
    async def get_verified_users(self, session: AsyncSession = Depends(get_session)):
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
    sort_default="-created_at", # sort by created_at in descending order
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
This project is licensed under the MIT License.
