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
