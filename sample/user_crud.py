import asyncio
import uuid
from typing import Dict, List

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from auto_crud.core.crud.base import BaseCRUD
from auto_crud.core.crud.decorators import action
from auto_crud.core.crud.router import RouterFactory
from auto_crud.core.schemas.pagination import (
    FilterParam,
    PaginatedResponse,
)
from auto_crud.dependencies.page_param import PageParams
from sample.db import get_session
from sample.hooks import UserHooks
from sample.models import User
from sample.schemas import (
    PostResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)

from .post_crud import post_crud


class UserRouterFactory(RouterFactory[User, uuid.UUID, UserCreate, UserUpdate]):
    @action(method="GET", detail=False, url_path="verified")
    async def get_verified_users(
        self, session: AsyncSession = Depends(get_session)
    ) -> List[UserResponse]:
        """Get all verified users"""
        filters = [
            FilterParam(field="is_verified", operator="eq", value=True),
            FilterParam(field="is_active", operator="eq", value=True),
        ]
        users = await self.crud.list_objects(session, filters=filters)
        return [UserResponse.model_validate(user) for user in users]

    @action(method="POST", detail=True, url_path="verify", status_code=200)
    async def verify_user(
        self, session: AsyncSession = Depends(get_session), *, id: uuid.UUID
    ) -> UserResponse:
        """Verify a user account"""
        user = await self.crud.get_by_id(session, id=id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        update_data = {"is_verified": True}
        updated_user = await self.crud.update(session, obj=user, obj_in=update_data)
        return UserResponse.model_validate(updated_user)

    @action(
        method="GET", detail=True, url_path="posts", response_model=PaginatedResponse[PostResponse]
    )
    async def get_user_posts(
        self,
        session: AsyncSession = Depends(get_session),
        *,
        id: uuid.UUID,
        page_params: PageParams = Depends(),
    ):
        """Get all posts by a user with pagination"""
        filters = [*page_params.filters, FilterParam(field="author_id", operator="eq", value=id)]
        return await post_crud.list_objects(
            session,
            filters=filters,
            search=page_params.search,
            search_fields=["title", "content"],
            sorting=page_params.sort_by,
            pagination={
                "page": page_params.page,
                "size": page_params.size,
            },
        )

    @action(
        method="GET",
        detail=True,
        url_path="followers",
        response_model=PaginatedResponse[UserResponse],
    )
    async def get_user_followers(
        self,
        session: AsyncSession = Depends(get_session),
        *,
        id: uuid.UUID,
        page_params: PageParams = Depends(),
    ) -> PaginatedResponse[User] | List[User]:
        user = await self.crud.get_by_id(session, id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        filters = [*page_params.filters, FilterParam(field="following.id", operator="eq", value=id)]

        return await self.crud.list_objects(
            session,
            filters=filters,
            search=page_params.search,
            search_fields=["username", "email", "full_name", "bio"],
            sorting=page_params.sort_by,
            pagination={
                "page": page_params.page,
                "size": page_params.size,
            },
        )

    @action(method="POST", detail=True, url_path="follow/{target_id}")
    async def follow_user(
        self,
        session: AsyncSession = Depends(get_session),
        *,
        id: uuid.UUID,
        target_id: uuid.UUID,
    ) -> Dict[str, str]:
        """Follow another user"""
        if id == target_id:
            raise HTTPException(status_code=400, detail="Cannot follow yourself")

        follower_task = self.crud.get_by_id(session, id, prefetch=["following"])
        target_task = self.crud.get_by_id(session, target_id)

        follower, target = await asyncio.gather(follower_task, target_task)

        if not follower or not target:
            raise HTTPException(status_code=404, detail="User not found")

        if any(user.id == target.id for user in follower.following):
            raise HTTPException(status_code=400, detail="Already following this user")

        follower.following.append(target)
        session.add(follower)
        await session.commit()

        return {"message": f"Successfully followed {target.username}"}

    @action(method="GET", detail=False, url_path="search")
    async def search_users(
        self,
        session: AsyncSession = Depends(get_session),
        *,
        q: str,
    ) -> List[UserResponse]:
        """Search users by username, email, or full name"""
        users = await self.crud.search(session, q, fields=["username", "email", "full_name"])
        return [UserResponse.model_validate(user) for user in users]


user_crud = BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User, hooks=UserHooks())

user_router_factory = UserRouterFactory(
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
    search_fields=["username", "email", "full_name", "bio"],
    sort_default="-created_at",
    page_size=20,
    max_page_size=100,
    response_schemas={
        "create": UserResponse,
        "update": UserResponse,
        "read": UserResponse,
        "list": UserResponse,
        "bulk_create": UserResponse,
        "bulk_update": UserResponse,
        "bulk_delete": UserResponse,
    },
    filter_spec={
        "full_name": ("eq", "contains"),
        "role": ("eq", "in"),
        "is_verified": ("eq",),
        "is_active": ("eq",),
    },
)

user_router = user_router_factory.get_router()
