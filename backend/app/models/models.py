from sqlalchemy import Column, String, Integer, Numeric, Boolean, Date, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid

def gen_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=False)
    national_id = Column(String(20), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    memberships = relationship("GroupMember", back_populates="user")
    created_groups = relationship("Group", back_populates="creator")

class Group(Base):
    __tablename__ = "groups"
    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    contribution_amount = Column(Numeric(10, 2), nullable=False)
    meeting_frequency = Column(String(50), nullable=False)
    meeting_day = Column(String(20))
    created_date = Column(Date, nullable=False)
    created_by = Column(String, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    creator = relationship("User", back_populates="created_groups")
    members = relationship("GroupMember", back_populates="group")
    contributions = relationship("Contribution", back_populates="group")
    loans = relationship("Loan", back_populates="group")
    meetings = relationship("Meeting", back_populates="group")
    credit_scores = relationship("CreditScore", back_populates="group")

class GroupMember(Base):
    __tablename__ = "group_members"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    group_id = Column(String, ForeignKey("groups.id"), nullable=False)
    role = Column(String(50), default="member")
    joined_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)
    user = relationship("User", back_populates="memberships")
    group = relationship("Group", back_populates="members")

class Contribution(Base):
    __tablename__ = "contributions"
    id = Column(String, primary_key=True, default=gen_uuid)
    group_id = Column(String, ForeignKey("groups.id"), nullable=False)
    member_id = Column(String, ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    contribution_date = Column(Date, nullable=False)
    payment_method = Column(String(50), default="mpesa")
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    group = relationship("Group", back_populates="contributions")
    member = relationship("User", foreign_keys=[member_id])

class Loan(Base):
    __tablename__ = "loans"
    id = Column(String, primary_key=True, default=gen_uuid)
    group_id = Column(String, ForeignKey("groups.id"), nullable=False)
    member_id = Column(String, ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    purpose = Column(String(255))
    application_date = Column(Date, nullable=False)
    approval_status = Column(String(50), default="pending")
    disbursed_date = Column(Date)
    repayment_date = Column(Date)
    interest_rate = Column(Numeric(5, 2), default=10.0)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, server_default=func.now())
    group = relationship("Group", back_populates="loans")
    member = relationship("User", foreign_keys=[member_id])
    repayments = relationship("LoanRepayment", back_populates="loan")
    approvals = relationship("LoanApproval", back_populates="loan")

class LoanRepayment(Base):
    __tablename__ = "loan_repayments"
    id = Column(String, primary_key=True, default=gen_uuid)
    loan_id = Column(String, ForeignKey("loans.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_date = Column(Date, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    loan = relationship("Loan", back_populates="repayments")

class LoanApproval(Base):
    __tablename__ = "loan_approvals"
    id = Column(String, primary_key=True, default=gen_uuid)
    loan_id = Column(String, ForeignKey("loans.id"), nullable=False)
    member_id = Column(String, ForeignKey("users.id"), nullable=False)
    approved = Column(Boolean, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    loan = relationship("Loan", back_populates="approvals")
    member = relationship("User", foreign_keys=[member_id])

class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(String, primary_key=True, default=gen_uuid)
    group_id = Column(String, ForeignKey("groups.id"), nullable=False)
    title = Column(String(255), nullable=False)
    date = Column(DateTime, nullable=False)
    agenda = Column(Text)
    minutes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    group = relationship("Group", back_populates="meetings")
    attendance = relationship("MeetingAttendance", back_populates="meeting")

class MeetingAttendance(Base):
    __tablename__ = "meeting_attendance"
    id = Column(String, primary_key=True, default=gen_uuid)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False)
    member_id = Column(String, ForeignKey("users.id"), nullable=False)
    attended = Column(Boolean, default=False)
    fine_amount = Column(Numeric(10, 2), default=0)
    meeting = relationship("Meeting", back_populates="attendance")
    member = relationship("User", foreign_keys=[member_id])

class CreditScore(Base):
    __tablename__ = "credit_scores"
    id = Column(String, primary_key=True, default=gen_uuid)
    group_id = Column(String, ForeignKey("groups.id"), nullable=False)
    score_date = Column(Date, nullable=False)
    score_value = Column(Integer, nullable=False)
    score_band = Column(String(50))
    features_json = Column(JSON, nullable=False)
    calculation_log = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    group = relationship("Group", back_populates="credit_scores")