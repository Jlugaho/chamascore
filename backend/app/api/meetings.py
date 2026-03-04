from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import Meeting
from app.schemas.schemas import MeetingCreate, MeetingOut
import uuid

router = APIRouter()

@router.post("", response_model=MeetingOut, status_code=201)
async def create_meeting(data: MeetingCreate, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    meeting = Meeting(
        id=str(uuid.uuid4()),
        group_id=data.group_id,
        title=data.title,
        date=data.date,
        agenda=data.agenda,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting

@router.get("/group/{group_id}", response_model=List[MeetingOut])
async def list_meetings(group_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return db.query(Meeting).filter(Meeting.group_id == group_id).order_by(Meeting.date.desc()).all()