from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    phone_number: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    role: str = "student"


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone_number: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ItemBase(BaseModel):
    title: str = Field(..., min_length=3)
    description: str = Field(..., min_length=3)
    item_type: Literal["lost", "found"]
    campus_location: str = Field(..., min_length=3)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3)
    description: Optional[str] = Field(None, min_length=3)
    campus_location: Optional[str] = Field(None, min_length=3)


class PhotoResponse(BaseModel):
    id: int
    image_url: str
    caption: Optional[str] = ""
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemResponse(ItemBase):
    id: int
    status: str
    is_resolved: bool
    user_id: int
    created_at: datetime
    user: UserResponse
    photos: list[PhotoResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ModerationReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    comments: str = ""

    @model_validator(mode="after")
    def validate_comments_for_rejection(self):
        if self.decision == "rejected" and (not self.comments or not self.comments.strip()):
            raise ValueError("Comments are required when rejecting an item")
        return self


class ModerationRecordResponse(BaseModel):
    id: int
    item_id: int
    admin_id: int
    decision: str
    comments: str
    reviewed_at: datetime

    model_config = ConfigDict(from_attributes=True)

