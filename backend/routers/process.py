from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from typing import Optional
from fastapi.responses import Response
from auth import optional_token
from database import get_db
from services.effects import EFFECT_MAP
from services.storage import upload_original, upload_result
import uuid

router = APIRouter(prefix="/api/process", tags=["process"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_MB = 10

# ── Process image synchronously (fast effects) ──────────────────────────────
@router.post("/{effect}")
async def process_image(
    effect: str,
    file: UploadFile = File(...),
    save: bool = Form(False),
    user=Depends(optional_token),
):
    if effect not in EFFECT_MAP:
        raise HTTPException(status_code=404, detail=f"Unknown effect: {effect}")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG/PNG/WEBP images accepted")

    img_bytes = await file.read()
    if len(img_bytes) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large (max {MAX_SIZE_MB}MB)")

    uid = user["sub"] if user else None

    # Create job record
    db = get_db()
    job_id = str(uuid.uuid4())
    db.table("processing_jobs").insert({
        "id": job_id,
        "user_id": uid,
        "status": "processing",
        "effect": effect,
    }).execute()

    try:
        fn = EFFECT_MAP[effect]
        result_bytes = fn(img_bytes)
    except Exception as e:
        db.table("processing_jobs").update(
            {"status": "failed", "error_message": str(e)}
        ).eq("id", job_id).execute()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

    # Optionally save to storage and project
    result_url = None
    if save and uid:
        ext = "png"
        result_url = upload_result(result_bytes, ext, uid)
        db.table("projects").insert({
            "user_id": uid,
            "title": f"{effect.replace('-', ' ').title()}",
            "effect_used": effect,
            "result_url": result_url,
        }).execute()

    db.table("processing_jobs").update({
        "status": "done",
        "output_path": result_url,
    }).eq("id", job_id).execute()

    return Response(
        content=result_bytes,
        media_type="image/png",
        headers={
            "X-Job-Id": job_id,
            "X-Result-URL": result_url or "",
        }
    )

# ── Job status ───────────────────────────────────────────────────────────────
@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    db = get_db()
    res = db.table("processing_jobs").select("*").eq("id", job_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return res.data
