import uuid
import io
from database import get_db
from config import STORAGE_BUCKET_ORIGINALS, STORAGE_BUCKET_RESULTS

def upload_original(file_bytes: bytes, ext: str, user_id: str | None = None) -> str:
    prefix = user_id or "anon"
    path = f"{prefix}/{uuid.uuid4()}.{ext}"
    db = get_db()
    db.storage.from_(STORAGE_BUCKET_ORIGINALS).upload(path, file_bytes,
        file_options={"content-type": f"image/{ext}"})
    return db.storage.from_(STORAGE_BUCKET_ORIGINALS).get_public_url(path)

def upload_result(file_bytes: bytes, ext: str, user_id: str | None = None) -> str:
    prefix = user_id or "anon"
    path = f"{prefix}/{uuid.uuid4()}.{ext}"
    db = get_db()
    db.storage.from_(STORAGE_BUCKET_RESULTS).upload(path, file_bytes,
        file_options={"content-type": f"image/{ext}"})
    return db.storage.from_(STORAGE_BUCKET_RESULTS).get_public_url(path)
