from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import Loan, LoanApproval
from app.schemas.schemas import LoanApplication, LoanOut
import uuid

router = APIRouter()

@router.post("/apply", response_model=LoanOut, status_code=201)
async def apply_loan(data: LoanApplication, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    loan = Loan(
        id=str(uuid.uuid4()),
        group_id=data.group_id,
        member_id=user_id,
        amount=data.amount,
        purpose=data.purpose,
        application_date=date.today(),
        repayment_date=data.repayment_date,
        interest_rate=data.interest_rate,
        approval_status="pending",
        status="pending",
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan

@router.get("/group/{group_id}", response_model=List[LoanOut])
async def list_loans(group_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return db.query(Loan).filter(Loan.group_id == group_id).order_by(Loan.application_date.desc()).all()

@router.post("/{loan_id}/approve")
async def approve_loan(loan_id: str, approved: bool, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    approval = LoanApproval(
        id=str(uuid.uuid4()),
        loan_id=loan_id,
        member_id=user_id,
        approved=approved,
    )
    db.add(approval)
    approvals = db.query(LoanApproval).filter(LoanApproval.loan_id == loan_id, LoanApproval.approved == True).count()
    from app.models.models import GroupMember
    total_members = db.query(GroupMember).filter(GroupMember.group_id == loan.group_id, GroupMember.is_active == True).count()
    if total_members > 0 and (approvals + 1) / total_members >= 0.7:
        loan.approval_status = "approved"
        loan.status = "active"
    db.commit()
    return {"message": "Vote recorded", "loan_id": loan_id, "approved": approved}