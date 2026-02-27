import io
import logging
import mimetypes
import os
import uuid

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from ...core.feature_flags import is_attachments_feature_enabled

logger = logging.getLogger(__name__)

ATTACHMENTS_BUCKET_ENDPOINT = os.getenv("ATTACHMENTS_BUCKET_ENDPOINT", "minio:9000")
ATTACHMENTS_BUCKET_ACCESS_KEY = os.getenv(
    "ATTACHMENTS_BUCKET_ACCESS_KEY", "minio_rag_user"
)
ATTACHMENTS_BUCKET_SECRET_KEY = os.getenv(
    "ATTACHMENTS_BUCKET_SECRET_KEY", "minio_rag_password"
)
ATTACHMENTS_BUCKET_NAME = os.getenv("ATTACHMENTS_BUCKET_NAME", "attachments")
ATTACHMENTS_BUCKET_REGION = os.getenv("ATTACHMENTS_BUCKET_REGION", "us-east-1")

# Lazily initialized S3 resources to avoid side-effects at import time
_s3_client = None
_s3_resource = None
_bucket = None
_bucket_initialized = False


def _get_s3():
    """Return lazily initialized (client, resource, bucket).

    This defers any network interaction until first use, making unit tests
    independent from a running MinIO/S3 service.
    """
    global _s3_client, _s3_resource, _bucket, _bucket_initialized

    if _s3_client is None or _s3_resource is None or _bucket is None:
        client = boto3.client(
            "s3",
            endpoint_url=f"http://{ATTACHMENTS_BUCKET_ENDPOINT}",
            aws_access_key_id=ATTACHMENTS_BUCKET_ACCESS_KEY,
            aws_secret_access_key=ATTACHMENTS_BUCKET_SECRET_KEY,
            region_name=ATTACHMENTS_BUCKET_REGION,
        )

        resource = boto3.resource(
            "s3",
            endpoint_url=f"http://{ATTACHMENTS_BUCKET_ENDPOINT}",
            aws_access_key_id=ATTACHMENTS_BUCKET_ACCESS_KEY,
            aws_secret_access_key=ATTACHMENTS_BUCKET_SECRET_KEY,
            region_name=ATTACHMENTS_BUCKET_REGION,
        )

        bucket_obj = resource.Bucket(ATTACHMENTS_BUCKET_NAME)

        _s3_client = client
        _s3_resource = resource
        _bucket = bucket_obj

        # Ensure bucket exists once on first real use (no import-time side effects)
        if is_attachments_feature_enabled() and not _bucket_initialized:
            try:
                client.head_bucket(Bucket=ATTACHMENTS_BUCKET_NAME)
            except ClientError:
                client.create_bucket(Bucket=ATTACHMENTS_BUCKET_NAME)
            _bucket_initialized = True

    return _s3_client, _s3_resource, _bucket


router = APIRouter(prefix="/attachments", tags=["attachments"])


def ensure_bucket_exists():
    """
    Ensure the bucket exists.
    """
    client, _resource, _bkt = _get_s3()
    try:
        client.head_bucket(Bucket=ATTACHMENTS_BUCKET_NAME)
    except ClientError:
        client.create_bucket(Bucket=ATTACHMENTS_BUCKET_NAME)


def delete_attachments_for_session(session_id: str):
    """
    Delete all attachments for a session.
    """
    client, resource, bucket = _get_s3()
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
    client, _resource, _bucket = _get_s3()
    try:
        attachment_id = str(uuid.uuid4())
        if file.filename:
            _, ext = os.path.splitext(file.filename)
            # TODO: Add checks to ensure that the user is authorized to upload
            # attachments
            # for this session_id.
            client.upload_fileobj(
                file.file,
                ATTACHMENTS_BUCKET_NAME,
                f"{session_id}/{attachment_id}{ext}",
            )
            return JSONResponse(
                content={
                    "message": "File uploaded successfully",
                    "filename": f"{attachment_id}{ext}",
                },
                status_code=201,
            )
        else:
            return JSONResponse(
                content={"message": "File name is required"}, status_code=400
            )
    except ClientError as e:
        logger.warning(f"File upload failed: {e}")
        return JSONResponse(
            content={"message": "File upload failed"},
            status_code=e.response["ResponseMetadata"]["HTTPStatusCode"],
        )


@router.get("/{session_id}/{attachment}")
async def get_attachment(session_id: str, attachment: str):
    """
    Get an attachment by its name.
    """
    client, _resource, _bucket = _get_s3()
    try:
        fileobj = io.BytesIO()
        # TODO: Add checks to ensure that the user is authorized to download
        # attachments
        # for this session_id.
        client.download_fileobj(
            ATTACHMENTS_BUCKET_NAME, f"{session_id}/{attachment}", fileobj
        )
        fileobj.seek(0)
        buffer = fileobj.read(1024)
        # Prefer high-accuracy MIME detection if optional dependency is available,
        # otherwise fall back to filename-based guessing.
        try:
            import magic as _magic  # type: ignore
        except Exception:
            _magic = None

        if _magic is not None:
            try:
                mime_type = _magic.from_buffer(buffer, True)
            except Exception:
                mime_type = (
                    mimetypes.guess_type(attachment)[0] or "application/octet-stream"
                )
        else:
            mime_type = (
                mimetypes.guess_type(attachment)[0] or "application/octet-stream"
            )
        fileobj.seek(0)
        return StreamingResponse(
            content=fileobj,
            media_type=mime_type,
            headers={"Content-Disposition": f"inline; filename={attachment}"},
        )
    except ClientError as e:
        logger.warning(f"File download failed: {e}")
        return JSONResponse(
            content={"message": "File download failed"},
            status_code=e.response["ResponseMetadata"]["HTTPStatusCode"],
        )
