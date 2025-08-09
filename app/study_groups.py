from fastapi import APIRouter, Depends, HTTPException, status
from .schemas import (
    StudyGroupCreate, StudyGroupResponse, StudyGroupJoin,
    DiscussionMessageCreate, DiscussionMessageResponse,
    GroupResourceCreate, GroupResourceResponse,
    GroupTimetableEventCreate, GroupTimetableEventResponse,
    StudyGroupMemberResponse
)
from .database import db
from .dependencies import get_current_user
from bson import ObjectId
from typing import List, Optional
from datetime import datetime, timezone
import secrets
import string
import base64
import os
from fastapi.responses import StreamingResponse

router = APIRouter(
    prefix="/study-groups",
    tags=["Study Groups"]
)

def generate_access_code() -> str:
    """Generate a unique 6-character access code for private groups"""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))

def get_user_initials(full_name: str) -> str:
    """Get user initials from full name"""
    if not full_name:
        return "U"
    names = full_name.strip().split()
    if len(names) == 1:
        return names[0][:2].upper()
    return (names[0][0] + names[-1][0]).upper()

def sanitize_group_for_user(group_doc: dict, user_id: str) -> dict:
    """Return a safe-to-send copy of group for the given user."""
    safe_group = dict(group_doc)
    # convert id to string for clients
    if isinstance(safe_group.get("_id"), ObjectId):
        safe_group["_id"] = str(safe_group["_id"])
    # hide access code if user is not the creator
    if safe_group.get("is_private") and safe_group.get("creator_id") != user_id:
        safe_group["access_code"] = None
    return safe_group

# Study Group CRUD Operations
@router.post("/", response_model=StudyGroupResponse)
def create_study_group(
    group: StudyGroupCreate,
    user=Depends(get_current_user)
):
    """Create a new study group"""
    group_doc = group.dict()
    group_doc["creator_id"] = str(user["_id"])
    group_doc["members"] = [str(user["_id"])]
    group_doc["member_count"] = 1
    now_utc = datetime.now(timezone.utc)
    group_doc["created_at"] = now_utc
    group_doc["last_activity"] = now_utc
    group_doc["is_active"] = True
    
    # Generate access code for private groups
    if group.is_private:
        group_doc["access_code"] = generate_access_code()
    
    group_doc["_id"] = ObjectId()
    db.study_groups.insert_one(group_doc)
    
    # Create creator membership record
    member_doc = {
        "_id": ObjectId(),
        "user_id": str(user["_id"]),
        "group_id": str(group_doc["_id"]),
        "role": "creator",
        "joined_at": datetime.utcnow()
    }
    db.group_members.insert_one(member_doc)
    
    safe = sanitize_group_for_user(group_doc, str(user["_id"]))
    return StudyGroupResponse(**safe)

@router.get("/", response_model=List[StudyGroupResponse])
def get_study_groups(
    course: Optional[str] = None,
    user=Depends(get_current_user)
):
    """Get all study groups (public ones + user's private groups)"""
    # Build query for public groups or groups user is a member of
    user_id = str(user["_id"])
    
    # Get groups where user is a member
    user_groups = list(db.study_groups.find({
        "members": user_id
    }))
    
    # Get public groups where user is not already a member
    public_groups_query = {"is_private": False}
    if course:
        public_groups_query["course"] = course
    
    public_groups = list(db.study_groups.find(public_groups_query))
    
    # Combine and deduplicate
    all_groups = {str(g["_id"]): g for g in user_groups}
    for group in public_groups:
        group_id = str(group["_id"])
        if group_id not in all_groups:
            all_groups[group_id] = group
    
    # Convert to response format with sanitization
    result = []
    for group in all_groups.values():
        safe = sanitize_group_for_user(group, user_id)
        result.append(StudyGroupResponse(**safe))
    return result

@router.get("/{group_id}", response_model=StudyGroupResponse)
def get_study_group(
    group_id: str,
    user=Depends(get_current_user)
):
    """Get a specific study group"""
    try:
        group = db.study_groups.find_one({"_id": ObjectId(group_id)})
        if not group:
            raise HTTPException(status_code=404, detail="Study group not found")
        
        # Check if user has access to private groups
        user_id = str(user["_id"])
        if group["is_private"] and user_id not in group["members"]:
            raise HTTPException(status_code=403, detail="Access denied to private group")
        
        safe = sanitize_group_for_user(group, str(user["_id"]))
        return StudyGroupResponse(**safe)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid group ID")

@router.post("/{group_id}/join")
def join_study_group(
    group_id: str,
    join_data: StudyGroupJoin,
    user=Depends(get_current_user)
):
    """Join a study group"""
    try:
        group = db.study_groups.find_one({"_id": ObjectId(group_id)})
        if not group:
            raise HTTPException(status_code=404, detail="Study group not found")
        
        user_id = str(user["_id"])
        
        # Check if user is already a member
        if user_id in group["members"]:
            raise HTTPException(status_code=400, detail="Already a member of this group")
        
        # Check group capacity
        if len(group["members"]) >= group["max_members"]:
            raise HTTPException(status_code=400, detail="Group is at maximum capacity")
        
        # Check access code for private groups
        if group["is_private"]:
            if not join_data.access_code or join_data.access_code != group["access_code"]:
                raise HTTPException(status_code=403, detail="Invalid access code")
        
        # Add user to group
        db.study_groups.update_one(
            {"_id": ObjectId(group_id)},
            {
                "$push": {"members": user_id},
                "$inc": {"member_count": 1},
                "$set": {"last_activity": datetime.now(timezone.utc)}
            }
        )
        
        # Create membership record
        member_doc = {
            "_id": ObjectId(),
            "user_id": user_id,
            "group_id": group_id,
            "role": "member",
            "joined_at": datetime.now(timezone.utc)
        }
        db.group_members.insert_one(member_doc)
        
        return {"message": "Successfully joined the group"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Invalid group ID")

@router.post("/join-by-code")
def join_study_group_by_code(
    join_data: StudyGroupJoin,
    user=Depends(get_current_user)
):
    """Join a study group using only an access code (for private groups)"""
    if not join_data.access_code:
        raise HTTPException(status_code=400, detail="Access code is required")
    
    # Find group by access code
    group = db.study_groups.find_one({"access_code": join_data.access_code})
    if not group:
        raise HTTPException(status_code=404, detail="Study group not found for this access code")

    group_id = str(group["_id"])
    user_id = str(user["_id"])

    # Already a member
    if user_id in group.get("members", []):
        return {"message": "Already a member of this group", "group_id": group_id}

    # Capacity check
    if len(group.get("members", [])) >= group.get("max_members", 0):
        raise HTTPException(status_code=400, detail="Group is at maximum capacity")

    # Add user to group
    db.study_groups.update_one(
        {"_id": ObjectId(group_id)},
        {
            "$push": {"members": user_id},
            "$inc": {"member_count": 1},
            "$set": {"last_activity": datetime.utcnow()}
        }
    )

    # Create membership record
    member_doc = {
        "_id": ObjectId(),
        "user_id": user_id,
        "group_id": group_id,
        "role": "member",
        "joined_at": datetime.utcnow()
    }
    db.group_members.insert_one(member_doc)

    return {"message": "Successfully joined the group", "group_id": group_id}

@router.delete("/{group_id}")
def delete_study_group(
    group_id: str,
    user=Depends(get_current_user)
):
    """Delete a study group. Only the creator can delete the group."""
    try:
        group = db.study_groups.find_one({"_id": ObjectId(group_id)})
        if not group:
            raise HTTPException(status_code=404, detail="Study group not found")
        
        user_id = str(user["_id"])
        if group.get("creator_id") != user_id:
            raise HTTPException(status_code=403, detail="Only the group creator can delete this group")
        
        # Delete the group
        db.study_groups.delete_one({"_id": ObjectId(group_id)})
        # Cascade delete related data
        db.group_members.delete_many({"group_id": group_id})
        db.discussion_messages.delete_many({"group_id": group_id})
        db.group_resources.delete_many({"group_id": group_id})
        db.group_timetable_events.delete_many({"group_id": group_id})
        
        return {"message": "Group deleted"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Invalid group ID")

@router.post("/{group_id}/leave")
def leave_study_group(
    group_id: str,
    user=Depends(get_current_user)
):
    """Leave a study group"""
    try:
        group = db.study_groups.find_one({"_id": ObjectId(group_id)})
        if not group:
            raise HTTPException(status_code=404, detail="Study group not found")
        
        user_id = str(user["_id"])
        
        # Check if user is a member
        if user_id not in group["members"]:
            raise HTTPException(status_code=400, detail="Not a member of this group")
        
        # Prevent creator from leaving if there are other members
        if group["creator_id"] == user_id and len(group["members"]) > 1:
            raise HTTPException(
                status_code=400, 
                detail="Group creator cannot leave while there are other members. Transfer ownership first."
            )
        
        # Remove user from group
        db.study_groups.update_one(
            {"_id": ObjectId(group_id)},
            {
                "$pull": {"members": user_id},
                "$inc": {"member_count": -1},
                "$set": {"last_activity": datetime.now(timezone.utc)}
            }
        )
        
        # Remove membership record
        db.group_members.delete_one({
            "user_id": user_id,
            "group_id": group_id
        })
        
        # If creator left and no other members, delete the group
        if group["creator_id"] == user_id and len(group["members"]) == 1:
            db.study_groups.delete_one({"_id": ObjectId(group_id)})
            # Clean up related data
            db.discussion_messages.delete_many({"group_id": group_id})
            db.group_resources.delete_many({"group_id": group_id})
            db.group_timetable_events.delete_many({"group_id": group_id})
            return {"message": "Left group and group was deleted"}
        
        return {"message": "Successfully left the group"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Invalid group ID")

@router.get("/{group_id}/members", response_model=List[StudyGroupMemberResponse])
def get_group_members(
    group_id: str,
    user=Depends(get_current_user)
):
    """Get all members of a study group"""
    try:
        # Verify user has access to the group
        group = db.study_groups.find_one({"_id": ObjectId(group_id)})
        if not group:
            raise HTTPException(status_code=404, detail="Study group not found")
        
        user_id = str(user["_id"])
        if group["is_private"] and user_id not in group["members"]:
            raise HTTPException(status_code=403, detail="Access denied to private group")
        
        # Get member details
        members = list(db.group_members.find({"group_id": group_id}))
        
        # Enrich with user information
        for member in members:
            user_info = db.users.find_one({"_id": ObjectId(member["user_id"])})
            if user_info:
                member["user_info"] = {
                    "username": user_info.get("username", ""),
                    "full_name": user_info.get("full_name", ""),
                    "initials": get_user_initials(user_info.get("full_name", ""))
                }
            member["_id"] = str(member["_id"])
        
        return [StudyGroupMemberResponse(**member) for member in members]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Invalid group ID")

# Discussion endpoints
@router.post("/{group_id}/discussions", response_model=DiscussionMessageResponse)
def create_discussion_message(
    group_id: str,
    message: DiscussionMessageCreate,
    user=Depends(get_current_user)
):
    """Create a new discussion message"""
    try:
        # Verify user is a member of the group
        group = db.study_groups.find_one({"_id": ObjectId(group_id)})
        if not group:
            raise HTTPException(status_code=404, detail="Study group not found")
        
        user_id = str(user["_id"])
        if user_id not in group["members"]:
            raise HTTPException(status_code=403, detail="Must be a group member to post messages")
        
        message_doc = message.dict()
        message_doc["user_id"] = user_id
        message_doc["user_name"] = user.get("full_name", user.get("username", "Unknown"))
        message_doc["user_initials"] = get_user_initials(user.get("full_name", ""))
        message_doc["created_at"] = datetime.now(timezone.utc)
        message_doc["_id"] = ObjectId()
        
        db.discussion_messages.insert_one(message_doc)
        
        # Update group last activity
        db.study_groups.update_one(
            {"_id": ObjectId(group_id)},
            {"$set": {"last_activity": datetime.now(timezone.utc)}}
        )
        
        message_doc["_id"] = str(message_doc["_id"])
        return DiscussionMessageResponse(**message_doc)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Invalid group ID")

@router.get("/{group_id}/discussions", response_model=List[DiscussionMessageResponse])
def get_discussion_messages(
    group_id: str,
    limit: int = 50,
    user=Depends(get_current_user)
):
    """Get discussion messages for a group"""
    try:
        # Verify user has access to the group
        group = db.study_groups.find_one({"_id": ObjectId(group_id)})
        if not group:
            raise HTTPException(status_code=404, detail="Study group not found")
        
        user_id = str(user["_id"])
        if group["is_private"] and user_id not in group["members"]:
            raise HTTPException(status_code=403, detail="Access denied to private group")
        
        messages = list(db.discussion_messages.find(
            {"group_id": group_id}
        ).sort("created_at", -1).limit(limit))
        
        for message in messages:
            message["_id"] = str(message["_id"])
        
        return [DiscussionMessageResponse(**message) for message in reversed(messages)]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Invalid group ID")

# Resource endpoints
@router.post("/{group_id}/resources", response_model=GroupResourceResponse)
def upload_group_resource(
    group_id: str,
    resource: GroupResourceCreate,
    user=Depends(get_current_user)
):
    """Upload a resource to a study group"""
    try:
        # Verify user is a member of the group
        group = db.study_groups.find_one({"_id": ObjectId(group_id)})
        if not group:
            raise HTTPException(status_code=404, detail="Study group not found")
        
        user_id = str(user["_id"])
        if user_id not in group["members"]:
            raise HTTPException(status_code=403, detail="Must be a group member to upload resources")
        
        # Keep base64 content to enable downloads (for demo; consider cloud storage in prod)
        resource_doc = resource.dict()
        resource_doc["file_base64"] = resource_doc.pop("file_content")
        resource_doc["uploaded_by"] = user_id
        resource_doc["uploader_name"] = user.get("full_name", user.get("username", "Unknown"))
        resource_doc["uploaded_at"] = datetime.now(timezone.utc)
        resource_doc["_id"] = ObjectId()
        resource_doc["download_url"] = f"/study-groups/{group_id}/resources/{str(resource_doc['_id'])}/download"
        
        db.group_resources.insert_one(resource_doc)
        
        # Update group last activity
        db.study_groups.update_one(
            {"_id": ObjectId(group_id)},
            {"$set": {"last_activity": datetime.now(timezone.utc)}}
        )
        
        resource_doc["_id"] = str(resource_doc["_id"])
        return GroupResourceResponse(**resource_doc)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Invalid group ID or file data")

@router.get("/{group_id}/resources", response_model=List[GroupResourceResponse])
def get_group_resources(
    group_id: str,
    user=Depends(get_current_user)
):
    """Get all resources for a study group"""
    try:
        # Verify user has access to the group
        group = db.study_groups.find_one({"_id": ObjectId(group_id)})
        if not group:
            raise HTTPException(status_code=404, detail="Study group not found")
        
        user_id = str(user["_id"])
        if group["is_private"] and user_id not in group["members"]:
            raise HTTPException(status_code=403, detail="Access denied to private group")
        
        resources = list(db.group_resources.find(
            {"group_id": group_id}
        ).sort("uploaded_at", -1))
        
        for resource in resources:
            resource["_id"] = str(resource["_id"])
        
        return [GroupResourceResponse(**resource) for resource in resources]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Invalid group ID")

@router.get("/{group_id}/resources/{resource_id}/download")
def download_group_resource(
    group_id: str,
    resource_id: str,
    user=Depends(get_current_user)
):
    """Download a resource's original file content (stored as base64 for demo)."""
    try:
        # Verify access
        group = db.study_groups.find_one({"_id": ObjectId(group_id)})
        if not group:
            raise HTTPException(status_code=404, detail="Study group not found")
        user_id = str(user["_id"])
        if group["is_private"] and user_id not in group["members"]:
            raise HTTPException(status_code=403, detail="Access denied to private group")

        resource = db.group_resources.find_one({"_id": ObjectId(resource_id), "group_id": group_id})
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        file_base64 = resource.get("file_base64")
        if not file_base64:
            raise HTTPException(status_code=404, detail="File content not available")

        try:
            file_bytes = base64.b64decode(file_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="Corrupted file data")

        filename = resource.get("name", "download")
        file_type = resource.get("file_type", "application/octet-stream")

        return StreamingResponse(
            iter([file_bytes]),
            media_type=file_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Invalid group or resource ID")

# Group Timetable endpoints
@router.post("/{group_id}/timetable", response_model=GroupTimetableEventResponse)
def create_group_timetable_event(
    group_id: str,
    event: GroupTimetableEventCreate,
    user=Depends(get_current_user)
):
    """Create a new group timetable event"""
    try:
        # Verify user is a member of the group
        group = db.study_groups.find_one({"_id": ObjectId(group_id)})
        if not group:
            raise HTTPException(status_code=404, detail="Study group not found")
        
        user_id = str(user["_id"])
        if user_id not in group["members"]:
            raise HTTPException(status_code=403, detail="Must be a group member to create events")
        
        event_doc = event.dict()
        event_doc["created_by"] = user_id
        event_doc["creator_name"] = user.get("full_name", user.get("username", "Unknown"))
        event_doc["created_at"] = datetime.now(timezone.utc)
        event_doc["attendees"] = [user_id]  # Creator is automatically attending
        event_doc["attendee_count"] = 1
        event_doc["_id"] = ObjectId()
        
        db.group_timetable_events.insert_one(event_doc)
        
        # Update group last activity
        db.study_groups.update_one(
            {"_id": ObjectId(group_id)},
            {"$set": {"last_activity": datetime.now(timezone.utc)}}
        )
        
        event_doc["_id"] = str(event_doc["_id"])
        return GroupTimetableEventResponse(**event_doc)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Invalid group ID or event data")

@router.get("/{group_id}/timetable", response_model=List[GroupTimetableEventResponse])
def get_group_timetable_events(
    group_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=Depends(get_current_user)
):
    """Get timetable events for a study group"""
    try:
        # Verify user has access to the group
        group = db.study_groups.find_one({"_id": ObjectId(group_id)})
        if not group:
            raise HTTPException(status_code=404, detail="Study group not found")
        
        user_id = str(user["_id"])
        if group["is_private"] and user_id not in group["members"]:
            raise HTTPException(status_code=403, detail="Access denied to private group")
        
        query = {"group_id": group_id}
        
        # Add date filtering if provided
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = datetime.fromisoformat(start_date)
            if end_date:
                date_filter["$lte"] = datetime.fromisoformat(end_date)
            query["start_time"] = date_filter
        
        events = list(db.group_timetable_events.find(query).sort("start_time", 1))
        
        for event in events:
            event["_id"] = str(event["_id"])
        
        return [GroupTimetableEventResponse(**event) for event in events]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Invalid group ID or date format")

@router.post("/{group_id}/timetable/{event_id}/attend")
def attend_group_event(
    group_id: str,
    event_id: str,
    user=Depends(get_current_user)
):
    """Mark attendance for a group event"""
    try:
        # Verify user is a member of the group
        group = db.study_groups.find_one({"_id": ObjectId(group_id)})
        if not group:
            raise HTTPException(status_code=404, detail="Study group not found")
        
        user_id = str(user["_id"])
        if user_id not in group["members"]:
            raise HTTPException(status_code=403, detail="Must be a group member to attend events")
        
        # Check if event exists
        event = db.group_timetable_events.find_one({"_id": ObjectId(event_id), "group_id": group_id})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Add user to attendees if not already attending
        if user_id not in event.get("attendees", []):
            db.group_timetable_events.update_one(
                {"_id": ObjectId(event_id)},
                {
                    "$push": {"attendees": user_id},
                    "$inc": {"attendee_count": 1}
                }
            )
            return {"message": "Successfully marked as attending"}
        else:
            return {"message": "Already marked as attending"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Invalid group ID or event ID")