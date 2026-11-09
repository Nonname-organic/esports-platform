"""
ファイルアップロードエンドポイント

- S3_BUCKET_NAME 設定時: S3 / Cloudflare R2（S3互換）へアップロードし署名付きURLを返す
- 未設定時: ローカルディスク（/app/uploads）へ保存し、同一オリジンの配信URLを返す
  （開発環境・単一VM運用のフォールバック。キーはUUIDで推測不可）
"""

import mimetypes
import re
import uuid
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.dependencies import CurrentUser
from app.core.storage import sign_url, storage_client

router = APIRouter(prefix="/upload", tags=["アップロード"])

# 保存キーの拡張子は Content-Type から決める。利用者が付けたファイル名の
# 拡張子（.html など）をそのまま使うと、配信時にその形式として解釈される。
ALLOWED_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB

# 大会説明などの添付ファイル用（画像 + ドキュメント）
ALLOWED_FILE_TYPES = {
    **ALLOWED_TYPES,
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "text/plain": "txt",
    "text/csv": "csv",
    "application/zip": "zip",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def _attachment_disposition(name: str) -> str:
    """ダウンロード名を安全にヘッダへ載せる（引用符・改行の混入を防ぎ、日本語名は RFC 5987 で渡す）。"""
    name = re.sub(r'[\x00-\x1f\x7f"\\/]', "_", name)[:200] or "file"
    ascii_name = name.encode("ascii", "replace").decode("ascii").replace("?", "_")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}"

LOCAL_UPLOAD_DIR = Path("/app/uploads")


def _store(key: str, contents: bytes, content_type: str, disposition: str | None = None) -> str:
    """S3/R2 またはローカルディスクへ保存し、参照URLを返す。"""
    if settings.S3_BUCKET_NAME:
        extra = {"ContentDisposition": disposition} if disposition else {}
        storage_client().put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=contents,
            ContentType=content_type,
            **extra,
        )
        return sign_url(key)
    # ローカルフォールバック（同一オリジン配信 / nginx経由で相対URLが解決される）
    path = LOCAL_UPLOAD_DIR / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(contents)
    return f"/api/v1/upload/local/{key}"


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    purpose: Literal["team_logo", "team_banner", "avatar"] = Query(default="team_logo"),
    current_user: CurrentUser = ...,
):
    """画像をアップロードして参照URLを返す"""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "JPEG・PNG・WebP・GIF のみアップロード可能です")

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(400, "ファイルサイズは5MB以下にしてください")

    key = f"uploads/{purpose}/{uuid.uuid4()}.{ALLOWED_TYPES[file.content_type]}"

    try:
        url = _store(key, contents, file.content_type)
        return {"url": url, "key": key}
    except (ClientError, BotoCoreError) as e:
        raise HTTPException(500, f"ストレージへのアップロードに失敗しました: {e.__class__.__name__}")
    except OSError:
        raise HTTPException(500, "ファイルの保存に失敗しました")


@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    purpose: Literal["tournament_attachment"] = Query(default="tournament_attachment"),
    current_user: CurrentUser = ...,
):
    """添付ファイル（PDF・画像・ドキュメント等）をアップロードして参照URL・メタ情報を返す"""
    if file.content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(400, "対応形式: 画像 / PDF / Word / Excel / テキスト / ZIP")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, "ファイルサイズは10MB以下にしてください")

    original_name = file.filename or "file"
    key = f"uploads/{purpose}/{uuid.uuid4()}.{ALLOWED_FILE_TYPES[file.content_type]}"

    try:
        url = _store(
            key, contents, file.content_type,
            disposition=_attachment_disposition(original_name),
        )
        return {
            "url": url,
            "key": key,
            "name": original_name,
            "size": len(contents),
            "content_type": file.content_type,
        }
    except (ClientError, BotoCoreError) as e:
        raise HTTPException(500, f"ストレージへのアップロードに失敗しました: {e.__class__.__name__}")
    except OSError:
        raise HTTPException(500, "ファイルの保存に失敗しました")


@router.get("/local/{path:path}")
async def get_local_upload(path: str):
    """ローカル保存ファイルの配信（S3未設定環境用）。キーはUUIDのため推測不可。"""
    base = LOCAL_UPLOAD_DIR.resolve()
    target = (base / path).resolve()
    # パストラバーサル防止（前方一致だと /app/uploads2 のような隣のディレクトリが通る）
    if not target.is_relative_to(base) or not target.is_file():
        raise HTTPException(404, "ファイルが見つかりません")
    media_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    return FileResponse(
        target, media_type=media_type, headers={"X-Content-Type-Options": "nosniff"},
    )
