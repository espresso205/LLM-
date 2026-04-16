"""Admin-only user management endpoints."""
from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin, hash_password
from ..database import get_db

router = APIRouter(prefix="/api/admin")


@router.get("/users")
async def list_users(admin: dict = Depends(require_admin)):
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT id, username, role, is_active, created_at, last_login FROM users ORDER BY created_at DESC"
    )
    return [dict(r) for r in rows]


@router.patch("/users/{user_id}")
async def update_user(user_id: str, body: dict, admin: dict = Depends(require_admin)):
    db = await get_db()
    rows = await db.execute_fetchall("SELECT id FROM users WHERE id=?", (user_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="User not found")

    updates = []
    params = []

    if "role" in body and body["role"] in ("user", "admin"):
        updates.append("role=?")
        params.append(body["role"])

    if "is_active" in body:
        updates.append("is_active=?")
        params.append(1 if body["is_active"] else 0)

    if "password" in body:
        if len(body["password"]) < 6:
            raise HTTPException(status_code=400, detail="Password too short")
        updates.append("password_hash=?")
        params.append(hash_password(body["password"]))

    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    params.append(user_id)
    await db.execute(f"UPDATE users SET {', '.join(updates)} WHERE id=?", params)
    await db.commit()
    return {"updated": user_id}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    db = await get_db()
    # Prevent deleting yourself
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    rows = await db.execute_fetchall("SELECT id FROM users WHERE id=?", (user_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="User not found")
    await db.execute("DELETE FROM users WHERE id=?", (user_id,))
    await db.commit()
    return {"deleted": user_id}
