"""S3 ストレージ共通ユーティリティ

添付ファイル等の署名付きURLは有効期限があるため、DB には `key` を保存し、
レスポンス生成時に毎回フレッシュな署名付きURLを再生成する（実質無期限）。
generate_presigned_url はローカル計算（ネットワーク不要）なので都度呼んでも軽量。
"""

from typing import Optional
from urllib.parse import unquote, urlparse

import boto3

from app.core.config import settings

# boto3 クライアントはスレッドセーフなので使い回す
_s3_client = None

# SigV4 署名付きURLの最大有効期限（7日）
PRESIGN_MAX_EXPIRES = 7 * 24 * 3600


def _client():
    global _s3_client
    if _s3_client is None:
        # S3_ENDPOINT_URL 設定時は Cloudflare R2 等のS3互換ストレージへ接続（$0構成）
        _s3_client = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL or None,
        )
    return _s3_client


def storage_client():
    """S3/R2 クライアント（endpoint_url 対応の共有クライアント / 公開API）。"""
    return _client()


def sign_url(key: str, expires: int = PRESIGN_MAX_EXPIRES) -> str:
    """S3 オブジェクトキーから署名付きGET URLを生成"""
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
        ExpiresIn=expires,
    )


def resign_stored_url(url: Optional[str]) -> Optional[str]:
    """DB に保存済みの S3 署名付きURLから key を逆算し、フレッシュな署名付きURLを返す。

    - 空 / 自バケット以外（外部URL・Discord CDN等）はそのまま返す
    - virtual-hosted 形式（bucket.s3.../key）と path 形式（s3.../bucket/key）の両対応
    - 解析失敗時は元の url にフォールバック
    """
    if not url:
        return url
    bucket = settings.S3_BUCKET_NAME
    if not bucket or bucket not in url:
        return url
    try:
        path = unquote(urlparse(url).path).lstrip("/")
        if path.startswith(f"{bucket}/"):
            path = path[len(bucket) + 1:]
        if not path:
            return url
        return sign_url(path)
    except Exception:
        return url


def sign_attachments(attachments: Optional[list]) -> list:
    """保存済み添付リストの各 url を key から再署名して返す。

    key が無い / 署名失敗時は既存の url をそのまま残す（graceful degradation）。
    """
    if not attachments:
        return []
    result = []
    for a in attachments:
        item = dict(a)
        key = item.get("key")
        if key:
            try:
                item["url"] = sign_url(key)
            except Exception:
                pass  # 認証情報が無い環境などでは保存済み url にフォールバック
        result.append(item)
    return result
