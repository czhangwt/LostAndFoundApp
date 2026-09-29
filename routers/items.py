import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from models import Item, Photo, User
from routers.users import get_current_user, get_optional_current_user
from schemas import ItemCreate, ItemResponse, ItemUpdate, PhotoResponse

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter()


@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_item(
    item_in: ItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = Item(
        title=item_in.title.strip(),
        description=item_in.description.strip(),
        item_type=item_in.item_type,
        campus_location=item_in.campus_location.strip(),
        status="pending",
        is_resolved=False,
        user_id=current_user.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/", response_model=List[ItemResponse])
@router.get("", response_model=List[ItemResponse], include_in_schema=False)
def list_items(
    include_pending: bool = False,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    query = db.query(Item)
    if not current_user:
        query = query.filter(Item.status == "approved")
    elif current_user.role == "admin" and include_pending:
        pass
    else:
        query = query.filter(or_(Item.status == "approved", Item.user_id == current_user.id))

    items = query.order_by(Item.created_at.desc()).all()
    return items


@router.get("/search", response_model=List[ItemResponse])
@router.get("/search/", response_model=List[ItemResponse], include_in_schema=False)
def search_items(
    q: Optional[str] = Query(None, description="Keyword search in title and description"),
    item_type: Optional[str] = Query(None, description="Filter by lost or found"),
    location: Optional[str] = Query(None, description="Filter by campus location"),
    is_resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    db: Session = Depends(get_db),
):
    query = db.query(Item).filter(Item.status == "approved")

    if q and q.strip():
        search_term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Item.title.ilike(search_term),
                Item.description.ilike(search_term),
            )
        )

    if item_type and item_type.lower() in ["lost", "found"]:
        query = query.filter(Item.item_type == item_type.lower())

    if location and location.strip():
        query = query.filter(Item.campus_location.ilike(f"%{location.strip()}%"))

    if is_resolved is not None:
        query = query.filter(Item.is_resolved == is_resolved)
    else:
        # Default behavior: show unresolved items first or all active items
        pass

    return query.order_by(Item.created_at.desc()).all()


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found",
        )
    return item


@router.put("/{item_id}", response_model=ItemResponse)
def update_item(
    item_id: int,
    item_update: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found",
        )

    # Ownership check: must be author or admin
    if item.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this item",
        )

    if item_update.title is not None:
        item.title = item_update.title.strip()
    if item_update.description is not None:
        item.description = item_update.description.strip()
    if item_update.campus_location is not None:
        item.campus_location = item_update.campus_location.strip()

    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}/resolve", response_model=ItemResponse)
def resolve_item(
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

    # Ownership check: must be author or admin
    if item.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to resolve this item",
        )

    item.is_resolved = True
    db.commit()
    db.refresh(item)
    return item


@router.post("/{item_id}/photos", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
@router.post("/{item_id}/photos/", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def upload_photo(
    item_id: int,
    file: UploadFile = File(...),
    caption: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found",
        )

    # Ownership check: must be author or admin
    if item.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to upload photos for this item",
        )

    # Validate file extension and MIME content-type
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS or file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported media type. Permitted formats are JPEG, PNG, and WebP.",
        )

    # Validate file size limit (<= 5 MB)
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum allowed limit of 5 MB.",
        )

    # Generate collision-resistant unique filename
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    with open(file_path, "wb") as f:
        f.write(content)

    # Persist Photo record
    photo = Photo(
        item_id=item.id,
        image_url=f"/uploads/{unique_filename}",
        caption=caption.strip() if caption else "",
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo
