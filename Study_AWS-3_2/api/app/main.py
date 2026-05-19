from fastapi import Depends, FastAPI, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .csv_exports import create_csv_download_url, enqueue_csv_export
from .models import CsvExportJob, CsvExportStatus, Task, TaskStatus
from .schemas import (
    CsvDownloadUrlResponse,
    CsvExportJobResponse,
    ErrorResponse,
    ImageUploadUrlRequest,
    ImageUploadUrlResponse,
    ImageViewUrlResponse,
    TaskInput,
    TaskResponse,
)
from .storage import create_cloudfront_signed_url, create_upload_url
from .config import settings

app = FastAPI(title="Study AWS 3 Task API", version="1.0.0")


@app.on_event("startup")
def startup() -> None:
    # Local practice helper. In AWS, run migrations from the bastion instead.
    Base.metadata.create_all(bind=engine)


def to_response(task: Task, include_picture_url: bool = False) -> TaskResponse:
    picture_url = None
    if include_picture_url and task.picture_s3_key:
        picture_url = create_cloudfront_signed_url(task.picture_s3_key)

    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=TaskStatus(task.status),
        pictureS3Key=task.picture_s3_key,
        pictureUrl=picture_url,
        createdAt=task.created_at,
        updatedAt=task.updated_at,
    )


def csv_job_to_response(job: CsvExportJob) -> CsvExportJobResponse:
    return CsvExportJobResponse(
        id=job.id,
        status=CsvExportStatus(job.status),
        s3Key=job.s3_key,
        errorMessage=job.error_message,
        createdAt=job.created_at,
        updatedAt=job.updated_at,
        completedAt=job.completed_at,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/tasks", response_model=list[TaskResponse])
def list_tasks(status: TaskStatus | None = None, db: Session = Depends(get_db)) -> list[TaskResponse]:
    stmt = select(Task)
    if status is not None:
        stmt = stmt.where(Task.status == status.value)
    tasks = db.scalars(stmt.order_by(Task.id)).all()
    return [to_response(task) for task in tasks]


@app.post("/api/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskInput, db: Session = Depends(get_db)) -> TaskResponse:
    task = Task(
        title=payload.title,
        description=payload.description,
        status=payload.status.value,
        picture_s3_key=payload.pictureS3Key,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return to_response(task)


@app.get("/api/tasks/{task_id}", response_model=TaskResponse, responses={404: {"model": ErrorResponse}})
def get_task(task_id: int, db: Session = Depends(get_db)) -> TaskResponse:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="タスクが見つかりません")
    return to_response(task, include_picture_url=True)


@app.put("/api/tasks/{task_id}", response_model=TaskResponse, responses={404: {"model": ErrorResponse}})
def update_task(task_id: int, payload: TaskInput, db: Session = Depends(get_db)) -> TaskResponse:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="タスクが見つかりません")

    task.title = payload.title
    task.description = payload.description
    task.status = payload.status.value
    task.picture_s3_key = payload.pictureS3Key
    db.commit()
    db.refresh(task)
    return to_response(task)


@app.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, responses={404: {"model": ErrorResponse}})
def delete_task(task_id: int, db: Session = Depends(get_db)) -> Response:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="タスクが見つかりません")

    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post(
    "/api/tasks/{task_id}/image-upload-url",
    response_model=ImageUploadUrlResponse,
    responses={404: {"model": ErrorResponse}},
)
def issue_image_upload_url(
    task_id: int,
    payload: ImageUploadUrlRequest,
    db: Session = Depends(get_db),
) -> ImageUploadUrlResponse:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="タスクが見つかりません")

    try:
        upload_url, s3_key = create_upload_url(task_id, payload.filename, payload.contentType)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    task.picture_s3_key = s3_key
    db.commit()
    return ImageUploadUrlResponse(uploadUrl=upload_url, s3Key=s3_key, expiresIn=settings.upload_url_expires_seconds)


@app.post(
    "/api/tasks/{task_id}/image-view-url",
    response_model=ImageViewUrlResponse,
    responses={404: {"model": ErrorResponse}},
)
def issue_image_view_url(task_id: int, db: Session = Depends(get_db)) -> ImageViewUrlResponse:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="タスクが見つかりません")
    if not task.picture_s3_key:
        raise HTTPException(status_code=404, detail="画像が登録されていません")

    try:
        picture_url = create_cloudfront_signed_url(task.picture_s3_key)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ImageViewUrlResponse(pictureUrl=picture_url, expiresIn=settings.view_url_expires_seconds)


@app.post("/api/csv-exports", response_model=CsvExportJobResponse, status_code=status.HTTP_201_CREATED)
def create_csv_export(db: Session = Depends(get_db)) -> CsvExportJobResponse:
    job = CsvExportJob(status=CsvExportStatus.pending.value)
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        enqueue_csv_export(job.id)
    except RuntimeError as exc:
        job.status = CsvExportStatus.failed.value
        job.error_message = str(exc)
        db.commit()
        db.refresh(job)

    return csv_job_to_response(job)


@app.get("/api/csv-exports/{job_id}", response_model=CsvExportJobResponse, responses={404: {"model": ErrorResponse}})
def get_csv_export(job_id: int, db: Session = Depends(get_db)) -> CsvExportJobResponse:
    job = db.get(CsvExportJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="CSV出力ジョブが見つかりません")
    return csv_job_to_response(job)


@app.post(
    "/api/csv-exports/{job_id}/download-url",
    response_model=CsvDownloadUrlResponse,
    responses={404: {"model": ErrorResponse}},
)
def issue_csv_download_url(job_id: int, db: Session = Depends(get_db)) -> CsvDownloadUrlResponse:
    job = db.get(CsvExportJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="CSV出力ジョブが見つかりません")
    if job.status != CsvExportStatus.complete.value or not job.s3_key:
        raise HTTPException(status_code=409, detail="CSV出力がまだ完了していません")

    try:
        download_url = create_csv_download_url(job.s3_key)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return CsvDownloadUrlResponse(downloadUrl=download_url, expiresIn=300)
