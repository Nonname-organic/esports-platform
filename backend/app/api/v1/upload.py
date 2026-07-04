"""
ファイルアップロードエンドポイント
- S3 に画像をアップロードして公開URLを返す
"""

import uuid
from typing import Literal

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException, UploadFile, File, Query

from app.core.config import settings
from app.core.dependencies import CurrentUser

router = APIRouter(prefix="/upload", tags=["アップロード"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB

# 大会説明などの添付ファイル用（画像 + ドキュメント）
ALLOWED_FILE_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    "text/plain", "text/csv",
    "application/zip",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    purpose: Literal["team_logo", "team_banner", "avatar"] = Query(default="team_logo"),
    current_user: CurrentUser = ...,
):
    """画像をS3にアップロードして公開URLを返す"""
    # バリデーション
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "JPEG・PNG・WebP・GIF のみアップロード可能です")

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(400, "ファイルサイズは5MB以下にしてください")

    # ファイル名生成
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "jpg"
    key = f"uploads/{purpose}/{uuid.uuid4()}.{ext}"

    try:
        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        s3.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=contents,
            ContentType=file.content_type,
        )

        # 署名付きURLを生成（7日間有効、デモ用）
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
            ExpiresIn=7 * 24 * 3600,
        )
        return {"url": url, "key": key}

    except ClientError as e:
        raise HTTPException(500, f"アップロードに失敗しました: {str(e)}")


@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    purpose: Literal["tournament_attachment"] = Query(default="tournament_attachment"),
    current_user: CurrentUser = ...,
):
    """添付ファイル（PDF・画像・ドキュメント等）をS3にアップロードして公開URL・メタ情報を返す"""
    if file.content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(400, "対応形式: 画像 / PDF / Word / Excel / テキスト / ZIP")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, "ファイルサイズは10MB以下にしてください")

    original_name = file.filename or "file"
    ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else "bin"
    key = f"uploads/{purpose}/{uuid.uuid4()}.{ext}"

    try:
        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        s3.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=contents,
            ContentType=file.content_type,
            # ブラウザでダウンロード時に元のファイル名を保持
            ContentDisposition=f'attachment; filename="{original_name}"',
        )
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
            ExpiresIn=7 * 24 * 3600,
        )
        return {
            "url": url,
            "key": key,
            "name": original_name,
            "size": len(contents),
            "content_type": file.content_type,
        }
    except ClientError as e:
        raise HTTPException(500, f"アップロードに失敗しました: {str(e)}")
