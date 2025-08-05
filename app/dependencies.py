from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from .token import verify_access_token
from .database import db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    user = db.users.find_one({"email": payload["sub"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user["_id"] = str(user["_id"])
    return user
