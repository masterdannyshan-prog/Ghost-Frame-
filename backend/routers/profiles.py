from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from auth import verify_token
from database import get_db

router = APIRouter(prefix="/api/profiles", tags=["profiles"])

class ProfileUpdate(BaseModel):
    username: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None

@router.get("/me")
def get_my_profile(user=Depends(verify_token)):
    uid = user["sub"]
    db = get_db()
    res = db.table("profiles").select("*").eq("id", uid).single().execute()
    if not res.data:
        # Auto-create profile on first access
        db.table("profiles").insert({"id": uid}).execute()
        return {"id": uid}
    return res.data

@router.patch("/me")
def update_profile(body: ProfileUpdate, user=Depends(verify_token)):
    uid = user["sub"]
    db = get_db()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")
    res = db.table("profiles").update(updates).eq("id", uid).execute()
    return res.data[0] if res.data else {}

@router.get("/{username}")
def get_profile_by_username(username: str):
    db = get_db()
    res = db.table("profiles").select("*").eq("username", username).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="User not found")
    return res.data
