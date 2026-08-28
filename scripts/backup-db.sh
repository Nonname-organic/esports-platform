#!/usr/bin/env bash
#
# PostgreSQL の日次バックアップ（ADR-0003）。
#
#   1. コンテナ内で pg_dump を実行して gzip 圧縮
#   2. ローカルに保存（既定 14 世代）
#   3. S3 互換ストレージ（Cloudflare R2 等）が設定されていればアップロード
#
# cron 例（毎日 03:15）:
#   15 3 * * * /opt/app/scripts/backup-db.sh >> /var/log/axelia-backup.log 2>&1
#
# 復元は scripts/restore-db.sh を使う。
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BACKUP_DIR="${BACKUP_DIR:-${APP_DIR}/backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
COMPOSE="${COMPOSE_CMD:-docker compose}"

cd "$APP_DIR"

# backend/.env から DB 名・ユーザーと R2 設定を読む（無ければ既定値）
if [ -f backend/.env ]; then
  # shellcheck disable=SC1091
  set -a; . ./backend/.env; set +a
fi
DB_NAME="${POSTGRES_DB:-esports_db}"
DB_USER="${POSTGRES_USER:-esports_user}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
FILE="${BACKUP_DIR}/${DB_NAME}-${STAMP}.sql.gz"

echo "[$(date -u +%FT%TZ)] バックアップ開始: ${FILE}"

# --clean --if-exists: 復元時に既存オブジェクトを落としてから作り直せる
$COMPOSE exec -T postgres \
  pg_dump -U "$DB_USER" -d "$DB_NAME" --clean --if-exists --no-owner \
  | gzip -9 > "$FILE"

SIZE=$(du -h "$FILE" | cut -f1)
# 中身が空でないことを確認する（pg_dump が失敗しても gzip は成功しうる）
if [ "$(gzip -dc "$FILE" | head -c 1 | wc -c)" -eq 0 ]; then
  echo "ERROR: バックアップが空です。削除して異常終了します"
  rm -f "$FILE"
  exit 1
fi
echo "  ローカル保存 完了 (${SIZE})"

# ── リモート保存（S3 互換。未設定ならスキップ） ────────────────────────────
if [ -n "${BACKUP_S3_BUCKET:-}" ] && command -v aws >/dev/null 2>&1; then
  ENDPOINT_ARG=""
  [ -n "${S3_ENDPOINT_URL:-}" ] && ENDPOINT_ARG="--endpoint-url ${S3_ENDPOINT_URL}"
  # shellcheck disable=SC2086
  if aws s3 cp "$FILE" "s3://${BACKUP_S3_BUCKET}/db/$(basename "$FILE")" $ENDPOINT_ARG; then
    echo "  リモート保存 完了: s3://${BACKUP_S3_BUCKET}/db/"
  else
    echo "  WARN: リモート保存に失敗（ローカルには残っています）"
  fi
else
  echo "  リモート保存 スキップ（BACKUP_S3_BUCKET 未設定 または aws CLI 無し）"
fi

# ── 世代整理 ───────────────────────────────────────────────────────────────
DELETED=$(find "$BACKUP_DIR" -name "${DB_NAME}-*.sql.gz" -mtime "+${KEEP_DAYS}" -print -delete | wc -l)
echo "  古い世代を削除: ${DELETED}件（${KEEP_DAYS}日より前）"
echo "[$(date -u +%FT%TZ)] バックアップ完了"
