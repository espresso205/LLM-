"""Internal-token middleware for scheduler endpoints."""
import hmac

from fastapi import Header, HTTPException
from .config import settings


async def verify_internal_token(x_internal_token: str = Header(...)):
    if not hmac.compare_digest(x_internal_token, settings.INTERNAL_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid internal token")
