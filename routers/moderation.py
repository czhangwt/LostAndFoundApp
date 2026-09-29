from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Item, ModerationRecord, User
from routers.users import get_current_user
from schemas import ItemResponse, ModerationRecordResponse, ModerationReviewRequest

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return current_user


@router.get("/pending", response_model=List[ItemResponse])
@router.get("/pending/", response_model=List[ItemResponse], include_in_schema=False)
def get_pending_items(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    items = (
        db.query(Item)
        .filter(Item.status == "pending")
        .order_by(Item.created_at.desc())
        .all()
    )
    return items


@router.post("/{item_id}/review", response_model=ModerationRecordResponse, status_code=status.HTTP_201_CREATED)
@router.post("/{item_id}/review/", response_model=ModerationRecordResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def review_item(
    item_id: int,
    review_in: ModerationReviewRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found",
        )

    item.status = review_in.decision
    record = ModerationRecord(
        item_id=item.id,
        admin_id=admin_user.id,
        decision=review_in.decision,
        comments=review_in.comments.strip() if review_in.comments else "",
        reviewed_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{item_id}/history", response_model=List[ModerationRecordResponse])
@router.get("/{item_id}/history/", response_model=List[ModerationRecordResponse], include_in_schema=False)
def get_moderation_history(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found",
        )

    # Permission check: admin or item author
    if current_user.role != "admin" and item.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view moderation history for this item",
        )

    records = (
        db.query(ModerationRecord)
        .filter(ModerationRecord.item_id == item_id)
        .order_by(ModerationRecord.reviewed_at.desc())
        .all()
    )
    return records
