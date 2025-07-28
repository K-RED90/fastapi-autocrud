from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from auto_crud.core.errors import FilterError

from .db import init_database
from .post_crud import category_router, post_router, tag_router

# from .user_crud import user_router
from .user_crud import user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    yield


app = FastAPI(
    title="FastAPI-AutoCRUD Comprehensive Example API",
    description="""
    Comprehensive example demonstrating all FastAPI-AutoCRUD features including:

    ## Core Features
    - **Full CRUD Operations**: Create, Read, Update, Delete with pagination
    - **Advanced Filtering**: Complex filters with multiple operators
    - **Search Functionality**: Full-text search across multiple fields
    - **Sorting**: Multi-field sorting with custom orders
    - **Bulk Operations**: Bulk create, update, and delete
    - **Custom Actions**: Extended endpoints with business logic

    ## Advanced Features
    - **Hooks System**: Pre/post hooks for all operations
    - **Custom Validation**: Business rule validation
    - **Status Management**: Draft, published, archived states

    ## Entity Relationships
    - **Users**: Authentication, roles, following system
    - **Posts**: Content management with categories and tags
    - **Categories**: Hierarchical organization
    - **Tags**: Flexible tagging system
    - **Comments**: Nested comment system
    - **Likes**: Social interaction tracking
    """,
    version="2.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(user_router, prefix="/api/v1")
app.include_router(post_router, prefix="/api/v1")
app.include_router(category_router, prefix="/api/v1")
app.include_router(tag_router, prefix="/api/v1")


@app.exception_handler(FilterError)
async def filter_error_handler(request: Request, exc: FilterError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(ValueError)
async def validation_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "FastAPI-AutoCRUD Comprehensive Example API",
        "version": "2.0.0",
        "features": [
            "Full CRUD operations with pagination",
            "Advanced filtering and search",
            "Custom actions and business logic",
            "Comprehensive hooks system",
            "Relationship management",
            "Analytics tracking",
            "Role-based permissions",
            "Bulk operations",
            "Computed fields",
            "Status management",
        ],
        "endpoints": {
            "users": "/api/v1/users",
            "posts": "/api/v1/posts",
            "categories": "/api/v1/categories",
            "tags": "/api/v1/tags",
        },
        "documentation": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}


if __name__ == "__main__":
    uvicorn.run("sample.main:app", host="0.0.0.0", port=8000, reload=True)
