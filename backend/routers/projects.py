from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from auth import verify_token
from database import get_db
from services.storage import upload_result
import uuid

router = APIRouter(prefix="/api/projects", tags=["projects"])

class ProjectCreate(BaseModel):
    title: str = "Untitled"
    effect_used: Optional[str] = None
    original_url: Optional[str] = None
    result_url: str
    thumbnail_url: Optional[str] = None
    is_public: bool = False

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    is_public: Optional[bool] = None

# ── List user's projects ────────────────────────────────────────────────────
@router.get("")
def list_projects(user=Depends(verify_token)):
    uid = user["sub"]
    db = get_db()
    res = (db.table("projects")
             .select("*")
             .eq("user_id", uid)
             .order("created_at", desc=True)
             .execute())
    return res.data

# ── Get single project ──────────────────────────────────────────────────────
@router.get("/{project_id}")
def get_project(project_id: str, user=Depends(verify_token)):
    uid = user["sub"]
    db = get_db()
    res = (db.table("projects")
             .select("*")
             .eq("id", project_id)
             .eq("user_id", uid)
             .single()
             .execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return res.data

# ── Create project ──────────────────────────────────────────────────────────
@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, user=Depends(verify_token)):
    uid = user["sub"]
    db = get_db()
    res = (db.table("projects")
             .insert({**body.model_dump(), "user_id": uid})
             .execute())
    return res.data[0]

# ── Update project ──────────────────────────────────────────────────────────
@router.patch("/{project_id}")
def update_project(project_id: str, body: ProjectUpdate, user=Depends(verify_token)):
    uid = user["sub"]
    db = get_db()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    res = (db.table("projects")
             .update(updates)
             .eq("id", project_id)
             .eq("user_id", uid)
             .execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return res.data[0]

# ── Delete project ──────────────────────────────────────────────────────────
@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, user=Depends(verify_token)):
    uid = user["sub"]
    db = get_db()
    db.table("projects").delete().eq("id", project_id).eq("user_id", uid).execute()

# ── Upload and save result from editor ──────────────────────────────────────
@router.post("/upload-result", status_code=status.HTTP_201_CREATED)
async def upload_result_route(
    file: UploadFile = File(...),
    title: str = Form("Untitled"),
    effect_used: str = Form(""),
    user=Depends(verify_token),
):
    uid = user["sub"]
    img_bytes = await file.read()
    if len(img_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 20MB)")
    result_url = upload_result(img_bytes, "png", uid)
    db = get_db()
    res = db.table("projects").insert({
        "user_id": uid,
        "title": title or "Untitled",
        "effect_used": effect_used or None,
        "result_url": result_url,
    }).execute()
    return res.data[0]
