"""POST /auth/login and POST /auth/register."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from ..auth import create_access_token, hash_password, verify_password, get_current_user
from ..database import get_db
from shared.models import RegisterRequest

router = APIRouter(prefix="/auth")


@router.post("/login")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT id, username, password_hash, role, is_active FROM users WHERE username=?",
        (form.username,),
    )
    if not rows:
        # Always verify against a dummy hash to prevent timing-based user enumeration
        verify_password(form.password, "$2b$12$AAAAAAAAAAAAAAAAAAAAAAaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        raise HTTPException(status_code=401, detail="Invalid username or password")
    user = rows[0]
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Account disabled")
    if not verify_password(form.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    await db.execute("UPDATE users SET last_login=? WHERE id=?", (now, user["id"]))
    await db.commit()

    token = create_access_token(
        {"sub": user["id"], "username": user["username"], "role": user["role"]}
    )
    return {"access_token": token, "token_type": "bearer", "role": user["role"]}


@router.post("/register", status_code=201)
async def register(body: RegisterRequest):
    import sqlite3
    db = await get_db()
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    user_id = str(uuid.uuid4())
    hashed = hash_password(body.password)
    try:
        await db.execute(
            "INSERT INTO users (id, username, password_hash, role) VALUES (?, ?, ?, 'user')",
            (user_id, body.username, hashed),
        )
        await db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username already taken")
    return {"id": user_id, "username": body.username, "role": "user"}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return {"id": user["id"], "username": user["username"], "role": user["role"]}
