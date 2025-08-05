from fastapi import APIRouter, HTTPException
from . import schemas, utils
from .database import db
from .token import create_access_token
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=schemas.UserResponse)
def signup(user: schemas.UserCreate):
    if db.users.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered.")
    if db.users.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already taken.")
    hashed_pw = utils.hash_password(user.password)
    user_doc = user.dict()
    user_doc["hashed_password"] = hashed_pw
    del user_doc["password"]
    result = db.users.insert_one(user_doc)
    user_doc["_id"] = str(result.inserted_id)
    return schemas.UserResponse(**user_doc)

@router.post("/login")
def login(user: schemas.UserLogin):
    existing_user = db.users.find_one({"email": user.email})
    if not existing_user or not utils.verify_password(user.password, existing_user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid email or password.")
    access_token_expires = timedelta(minutes=1440)
    access_token = create_access_token(
        data={"sub": existing_user["email"]},
        expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(existing_user["_id"]),
            "username": existing_user["username"],
            "email": existing_user["email"],
            "full_name": existing_user.get("full_name"),
            "institution": existing_user.get("institution")
        }
    }
