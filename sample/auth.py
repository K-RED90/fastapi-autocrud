# Lets try basic auth
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from sample.models import User


async def get_user_by_credentials(
    credentials: HTTPBasicCredentials = Depends(HTTPBasic()),
) -> User:
    user = await get_user_by_credentials(credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return user
