from datetime import datetime

from pydantic import BaseModel, Field

from .models import TaskStatus


class TaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: TaskStatus = TaskStatus.pending
    pictureS3Key: str | None = Field(default=None, max_length=1024)


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    status: TaskStatus
    pictureS3Key: str | None = None
    pictureUrl: str | None = None
    createdAt: datetime
    updatedAt: datetime


class ImageUploadUrlRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    contentType: str = Field(default="image/jpeg", max_length=128)


class ImageUploadUrlResponse(BaseModel):
    uploadUrl: str
    s3Key: str
    expiresIn: int


class ImageViewUrlResponse(BaseModel):
    pictureUrl: str
    expiresIn: int


class ErrorResponse(BaseModel):
    message: str

