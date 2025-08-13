from botocore.exceptions import ClientError
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse, Response
from ..utils.logging_config import get_logger
import io
import os
import boto3
import magic
import uuid

logger = get_logger(__name__)

ATTACHMENTS_BUCKET_ENDPOINT = os.getenv("ATTACHMENTS_BUCKET_ENDPOINT", "minio:9000")
ATTACHMENTS_BUCKET_ACCESS_KEY = os.getenv("ATTACHMENTS_BUCKET_ACCESS_KEY", "minio_rag_user")
ATTACHMENTS_BUCKET_SECRET_KEY = os.getenv("ATTACHMENTS_BUCKET_SECRET_KEY", "minio_rag_password")
ATTACHMENTS_BUCKET_NAME = os.getenv("ATTACHMENTS_BUCKET_NAME", "attachments")
ATTACHMENTS_BUCKET_REGION = os.getenv("ATTACHMENTS_BUCKET_REGION", "us-east-1")
s3client = boto3.client(
    "s3",
    endpoint_url=f"http://{ATTACHMENTS_BUCKET_ENDPOINT}",
    aws_access_key_id=ATTACHMENTS_BUCKET_ACCESS_KEY,
    aws_secret_access_key=ATTACHMENTS_BUCKET_SECRET_KEY,
    region_name=ATTACHMENTS_BUCKET_REGION
)

s3resource = boto3.resource(
    "s3",
    endpoint_url=f"http://{ATTACHMENTS_BUCKET_ENDPOINT}",
    aws_access_key_id=ATTACHMENTS_BUCKET_ACCESS_KEY,
    aws_secret_access_key=ATTACHMENTS_BUCKET_SECRET_KEY,
    region_name=ATTACHMENTS_BUCKET_REGION
)

bucket = s3resource.Bucket(ATTACHMENTS_BUCKET_NAME)

router = APIRouter(prefix="/attachments", tags=["attachments"])

def ensure_bucket_exists():
    """
    Ensure the bucket exists.
    """
    try:
        s3client.head_bucket(Bucket=ATTACHMENTS_BUCKET_NAME)
    except ClientError:
        s3client.create_bucket(Bucket=ATTACHMENTS_BUCKET_NAME)

if os.getenv("DISABLE_ATTACHMENTS") != "true":
    ensure_bucket_exists()

def delete_attachments_for_session(session_id: str):
    """
    Delete all attachments for a session.
    """
    try:
        bucket.objects.filter(Prefix=f"{session_id}/").delete()
    except ClientError as e:
        logger.warning(f"Failed to delete attachments for session {session_id}: {e}")
        raise


@router.post("/")
async def upload_attachment(session_id: str = Form(...), file: UploadFile = File(...)):
    """
    Upload an attachment to the bucket.
    """
    try:
        attachment_id = str(uuid.uuid4())
        if file.filename:
            _, ext = os.path.splitext(file.filename)
            # TODO: Add checks to ensure that the user is authorized to upload attachments
            # for this session_id.
            s3client.upload_fileobj(file.file, ATTACHMENTS_BUCKET_NAME, f"{session_id}/{attachment_id}{ext}")
            return JSONResponse(content={"message": "File uploaded successfully", "filename": f"{attachment_id}{ext}"}, status_code=201)
        else:
            return JSONResponse(content={"message": "File name is required"}, status_code=400)
    except ClientError as e:
        logger.warning(f"File upload failed: {e}")
        return JSONResponse(content={"message": "File upload failed"}, status_code=e.response["ResponseMetadata"]["HTTPStatusCode"])

@router.get("/{session_id}/{attachment}")
async def get_attachment(session_id: str, attachment: str):
    """
    Get an attachment by its name.
    """
    try:
        fileobj = io.BytesIO()
        # TODO: Add checks to ensure that the user is authorized to download attachments
        # for this session_id.
        s3client.download_fileobj(ATTACHMENTS_BUCKET_NAME, f"{session_id}/{attachment}", fileobj)
        fileobj.seek(0)
        buffer = fileobj.read(1024)
        mime_type = magic.from_buffer(buffer, True)
        fileobj.seek(0)
        return StreamingResponse(content=fileobj, media_type=mime_type, headers={"Content-Disposition": f"inline; filename={attachment}"})
    except ClientError as e:
        logger.warning(f"File download failed: {e}")
        return JSONResponse(content={"message": "File download failed"}, status_code=e.response["ResponseMetadata"]["HTTPStatusCode"])
