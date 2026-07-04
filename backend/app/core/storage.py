"""S3 ストレージ共通ユーティリティ

添付ファイル等の署名付きURLは有効期限があるため、DB には `key` を保存し、
レスポンス生成時に毎回フレッシュな署名付きURLを再生成する（実質無期限）。
generate_presigned_url はローカル計算（ネットワーク不要）なので都度呼んでも軽量。
"""

from typing import Optional

import boto3

from app.core.config import settings

# boto3 クライアントはスレッドセーフなので使い回す
_s3_client = None

# SigV4 署名付きURLの最大有効期限（7日）
PRESIGN_MAX_EXPIRES = 7 * 24 * 3600


def _client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3", region_name=settings.AWS_REGION)
    return _s3_client


def sign_url(key: str, expires: int = PRESIGN_MAX_EXPIRES) -> str:
    """S3 オブジェクトキーから署名付きGET URLを生成"""
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
        ExpiresIn=expires,
    )


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
