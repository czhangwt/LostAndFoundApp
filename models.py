from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="student")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    items = relationship("Item", back_populates="user", cascade="all, delete-orphan")


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    item_type = Column(String, nullable=False)  # 'lost' or 'found'
    campus_location = Column(String, nullable=False, index=True)
    status = Column(String, default="pending", nullable=False, index=True)  # 'pending', 'approved', 'rejected'
    is_resolved = Column(Boolean, default=False, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="items")
    photos = relationship("Photo", back_populates="item", cascade="all, delete-orphan")
    moderation_records = relationship("ModerationRecord", back_populates="item", cascade="all, delete-orphan")


class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    image_url = Column(String, nullable=False)
    caption = Column(String(255), nullable=True, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    item = relationship("Item", back_populates="photos")


class ModerationRecord(Base):
    __tablename__ = "moderation_records"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    decision = Column(String, nullable=False)  # 'approved' or 'rejected'
    comments = Column(Text, nullable=False)
    reviewed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    item = relationship("Item", back_populates="moderation_records")
    admin = relationship("User")
