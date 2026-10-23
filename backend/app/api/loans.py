from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List
from datetime import date
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import Loan, LoanApproval, GroupMember
from app.schemas.schemas import LoanApplication, LoanOut
from app.api.dependencies import require_active_group_member
import uuid

router = APIRouter()

@router.post("/apply", response_model=LoanOut, status_code=201)
async def apply_loan(data: LoanApplication, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    require_active_group_member(data.group_id, user_id, db)
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
    require_active_group_member(group_id, user_id, db)
    return db.query(Loan).filter(Loan.group_id == group_id).order_by(Loan.application_date.desc()).all()

@router.post("/{loan_id}/approve")
async def approve_loan(loan_id: str, approved: bool, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    # Lock the loan before checking for an existing vote so concurrent requests
    # for this loan are serialized on both PostgreSQL and SQLite.
    locked = db.query(Loan).filter(Loan.id == loan_id).update(
        {Loan.status: Loan.status}, synchronize_session=False
    )
    if not locked:
        raise HTTPException(status_code=404, detail="Loan not found")
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    require_active_group_member(loan.group_id, user_id, db)
    if loan.approval_status != "pending":
        raise HTTPException(status_code=409, detail="Loan voting is closed")
    existing_vote = db.query(LoanApproval).filter(
        LoanApproval.loan_id == loan_id,
        LoanApproval.member_id == user_id,
    ).first()
    if existing_vote:
        raise HTTPException(status_code=409, detail="You have already voted on this loan")

    approval = LoanApproval(
        id=str(uuid.uuid4()),
        loan_id=loan_id,
        member_id=user_id,
        approved=approved,
    )
    db.add(approval)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        duplicate_vote = db.query(LoanApproval).filter(
            LoanApproval.loan_id == loan_id,
            LoanApproval.member_id == user_id,
        ).first()
        if duplicate_vote:
            raise HTTPException(status_code=409, detail="You have already voted on this loan")
        raise

    approvals = db.query(LoanApproval).filter(
        LoanApproval.loan_id == loan_id,
        LoanApproval.approved.is_(True),
    ).count()
    rejections = db.query(LoanApproval).filter(
        LoanApproval.loan_id == loan_id,
        LoanApproval.approved.is_(False),
    ).count()
    total_members = db.query(GroupMember).filter(
        GroupMember.group_id == loan.group_id,
        GroupMember.is_active.is_(True),
    ).count()
    if total_members and approvals / total_members >= 0.7:
        loan.approval_status = "approved"
        loan.status = "active"
    db.commit()
    return {
        "message": "Vote recorded",
        "loan_id": loan_id,
        "approved": approved,
        "yes_votes": approvals,
        "no_votes": rejections,
        "active_members": total_members,
        "approval_status": loan.approval_status,
    }