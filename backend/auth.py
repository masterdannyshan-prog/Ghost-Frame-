from fastapi import Header, HTTPException, status
from database import get_db

def verify_token(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    try:
        db = get_db()
        res = db.auth.get_user(token)
        if not res or not res.user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return {"sub": res.user.id, "email": res.user.email, "role": "authenticated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def optional_token(authorization: str = Header(None)) -> dict | None:
    if not authorization:
        return None
    try:
        return verify_token(authorization)
    except HTTPException:
        return None
