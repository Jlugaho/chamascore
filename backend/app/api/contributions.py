from fastapi import APIRouter, Depends, HTTPException, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import Contribution, GroupMember
from app.schemas.schemas import ContributionCreate, ContributionOut
from app.api.dependencies import require_active_group_member
import uuid

router = APIRouter()

@router.post("", response_model=ContributionOut, status_code=201)
async def record_contribution(data: ContributionCreate, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    require_active_group_member(data.group_id, user_id, db)
    member = db.query(GroupMember).filter(
        GroupMember.group_id == data.group_id,
        GroupMember.user_id == data.member_id,
        GroupMember.is_active.is_(True),
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Group member not found")
    contribution = Contribution(
        id=str(uuid.uuid4()),
        group_id=data.group_id,
        member_id=data.member_id,
        amount=data.amount,
        contribution_date=data.contribution_date,
        payment_method=data.payment_method,
        notes=data.notes,
    )
    db.add(contribution)
    db.commit()
    db.refresh(contribution)
    return contribution

@router.get("/group/{group_id}", response_model=List[ContributionOut])
async def list_contributions(group_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    require_active_group_member(group_id, user_id, db)
    return db.query(Contribution).filter(Contribution.group_id == group_id).order_by(Contribution.contribution_date.desc()).all()