from fastapi import APIRouter, Depends, HTTPException
from .schemas import StudyBlockCreate, StudyBlockResponse
from .database import db
from .dependencies import get_current_user
from bson import ObjectId
from typing import List

router = APIRouter(
    prefix="/timetable",
    tags=["Timetable"]
)

@router.post("/blocks", response_model=StudyBlockResponse)
def create_study_block(
    block: StudyBlockCreate,
    user=Depends(get_current_user)
):
    """Create a new study block"""
    block_doc = block.dict()
    block_doc["user_id"] = str(user["_id"])
    block_doc["_id"] = ObjectId()
    db.study_blocks.insert_one(block_doc)
    block_doc["_id"] = str(block_doc["_id"])
    return StudyBlockResponse(**block_doc)

@router.get("/blocks", response_model=List[StudyBlockResponse])
def get_study_blocks(
    user=Depends(get_current_user)
):
    """Get all study blocks for the current user"""
    blocks = list(db.study_blocks.find({"user_id": str(user["_id"])}))
    for block in blocks:
        block["_id"] = str(block["_id"])
    return [StudyBlockResponse(**block) for block in blocks]

@router.put("/blocks/{block_id}", response_model=StudyBlockResponse)
def update_study_block(
    block_id: str,
    block: StudyBlockCreate,
    user=Depends(get_current_user)
):
    """Update a study block"""
    # Check if block exists and belongs to user
    existing_block = db.study_blocks.find_one({
        "_id": ObjectId(block_id),
        "user_id": str(user["_id"])
    })
    
    if not existing_block:
        raise HTTPException(status_code=404, detail="Study block not found")
    
    # Update the block
    block_doc = block.dict()
    block_doc["user_id"] = str(user["_id"])
    
    result = db.study_blocks.update_one(
        {"_id": ObjectId(block_id), "user_id": str(user["_id"])},
        {"$set": block_doc}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Study block not found")
    
    # Return the updated block
    updated_block = db.study_blocks.find_one({"_id": ObjectId(block_id)})
    updated_block["_id"] = str(updated_block["_id"])
    return StudyBlockResponse(**updated_block)

@router.delete("/blocks/{block_id}")
def delete_study_block(
    block_id: str,
    user=Depends(get_current_user)
):
    """Delete a study block"""
    result = db.study_blocks.delete_one({
        "_id": ObjectId(block_id),
        "user_id": str(user["_id"])
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Study block not found")
    
    return {"message": "Study block deleted successfully"}

@router.delete("/blocks")
def clear_all_blocks(
    user=Depends(get_current_user)
):
    """Clear all study blocks for the current user"""
    result = db.study_blocks.delete_many({"user_id": str(user["_id"])})
    return {"message": f"Deleted {result.deleted_count} study blocks"}

@router.post("/blocks/bulk", response_model=List[StudyBlockResponse])
def create_multiple_blocks(
    blocks: List[StudyBlockCreate],
    user=Depends(get_current_user)
):
    """Create multiple study blocks at once (for auto-allocation)"""
    if not blocks:
        raise HTTPException(status_code=400, detail="No blocks provided")
    
    # Clear existing blocks first
    db.study_blocks.delete_many({"user_id": str(user["_id"])})
    
    # Create new blocks
    block_docs = []
    for block in blocks:
        block_doc = block.dict()
        block_doc["user_id"] = str(user["_id"])
        block_doc["_id"] = ObjectId()
        block_docs.append(block_doc)
    
    if block_docs:
        db.study_blocks.insert_many(block_docs)
    
    # Return the created blocks
    created_blocks = []
    for block_doc in block_docs:
        block_doc["_id"] = str(block_doc["_id"])
        created_blocks.append(StudyBlockResponse(**block_doc))
    
    return created_blocks 