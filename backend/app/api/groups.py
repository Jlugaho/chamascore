from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import Group, GroupMember
from app.schemas.schemas import GroupCreate, GroupOut
import uuid

router = APIRouter()

@router.post("", response_model=GroupOut, status_code=201)
async def create_group(data: GroupCreate, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    group = Group(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description,
        contribution_amount=data.contribution_amount,
        meeting_frequency=data.meeting_frequency,
        meeting_day=data.meeting_day,
        created_date=data.created_date,
        created_by=user_id,
    )
    db.add(group)
    db.flush()

    membership = GroupMember(
        id=str(uuid.uuid4()),
        user_id=user_id,
        group_id=group.id,
        role="chairperson",
        joined_date=date.today(),
    )
    db.add(membership)
    db.commit()
    db.refresh(group)
    return group

@router.get("", response_model=List[GroupOut])
async def list_groups(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    memberships = db.query(GroupMember).filter(GroupMember.user_id == user_id, GroupMember.is_active == True).all()
    group_ids = [m.group_id for m in memberships]
    return db.query(Group).filter(Group.id.in_(group_ids), Group.is_active == True).all()

@router.get("/{group_id}", response_model=GroupOut)
async def get_group(group_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id, Group.is_active == True).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group