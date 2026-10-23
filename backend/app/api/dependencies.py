from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import GroupMember


def require_active_group_member(group_id: str, user_id: str, db: Session) -> GroupMember:
    membership = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id,
        GroupMember.is_active.is_(True),
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Group not found")
    return membership
