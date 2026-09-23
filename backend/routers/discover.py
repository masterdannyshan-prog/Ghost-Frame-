from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from typing import Optional
from auth import verify_token, optional_token
from database import get_db

router = APIRouter(prefix="/api/discover", tags=["discover"])

class PostCreate(BaseModel):
    title: str
    description: Optional[str] = None
    tags: list[str] = []
    image_url: str
    effect_used: Optional[str] = None
    project_id: Optional[str] = None

# ── List posts (public, paginated) ─────────────────────────────────────────
@router.get("")
def list_posts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=50),
    tag: Optional[str] = None,
    effect: Optional[str] = None,
    user=Depends(optional_token),
):
    db = get_db()
    offset = (page - 1) * limit
    q = db.table("discover_posts").select(
        "*, profiles(username, avatar_url)"
    ).order("created_at", desc=True).range(offset, offset + limit - 1)

    if tag:
        q = q.contains("tags", [tag])
    if effect:
        q = q.eq("effect_used", effect)

    res = q.execute()

    # If logged in, mark which posts the user has liked
    liked_ids = set()
    if user:
        uid = user["sub"]
        likes = (db.table("discover_likes")
                   .select("post_id")
                   .eq("user_id", uid)
                   .execute())
        liked_ids = {r["post_id"] for r in likes.data}

    posts = res.data
    for p in posts:
        p["liked"] = p["id"] in liked_ids

    return {"posts": posts, "page": page, "limit": limit}

# ── Get single post ─────────────────────────────────────────────────────────
@router.get("/{post_id}")
def get_post(post_id: str):
    db = get_db()
    res = (db.table("discover_posts")
             .select("*, profiles(username, avatar_url)")
             .eq("id", post_id)
             .single()
             .execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Post not found")
    return res.data

# ── Create post ─────────────────────────────────────────────────────────────
@router.post("", status_code=status.HTTP_201_CREATED)
def create_post(body: PostCreate, user=Depends(verify_token)):
    uid = user["sub"]
    db = get_db()
    res = (db.table("discover_posts")
             .insert({**body.model_dump(), "user_id": uid})
             .execute())
    return res.data[0]

# ── Delete post ─────────────────────────────────────────────────────────────
@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: str, user=Depends(verify_token)):
    uid = user["sub"]
    db = get_db()
    db.table("discover_posts").delete().eq("id", post_id).eq("user_id", uid).execute()

# ── Toggle like ─────────────────────────────────────────────────────────────
@router.post("/{post_id}/like")
def toggle_like(post_id: str, user=Depends(verify_token)):
    uid = user["sub"]
    db = get_db()

    existing = (db.table("discover_likes")
                  .select("id")
                  .eq("user_id", uid)
                  .eq("post_id", post_id)
                  .execute())

    if existing.data:
        db.table("discover_likes").delete().eq("user_id", uid).eq("post_id", post_id).execute()
        db.table("discover_posts").update({"likes_count": db.rpc("decrement", {"x": 1})}).eq("id", post_id).execute()
        db.rpc("decrement_likes", {"post_id": post_id}).execute()
        return {"liked": False}
    else:
        db.table("discover_likes").insert({"user_id": uid, "post_id": post_id}).execute()
        db.rpc("increment_likes", {"post_id": post_id}).execute()
        return {"liked": True}
