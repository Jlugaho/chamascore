from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import Contribution
from app.schemas.schemas import ContributionCreate, ContributionOut
import uuid

router = APIRouter()

@router.post("", response_model=ContributionOut, status_code=201)
async def record_contribution(data: ContributionCreate, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
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
    return db.query(Contribution).filter(Contribution.group_id == group_id).order_by(Contribution.contribution_date.desc()).all()