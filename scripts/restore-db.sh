#!/usr/bin/env bash
#
# バックアップからのリストア（ADR-0003）。
#
#   scripts/restore-db.sh backups/esports_db-20260828-031500.sql.gz
#   scripts/restore-db.sh --latest
#
# 既存データを上書きするため、実行前に確認を求める。
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BACKUP_DIR="${BACKUP_DIR:-${APP_DIR}/backups}"
COMPOSE="${COMPOSE_CMD:-docker compose}"

cd "$APP_DIR"
if [ -f backend/.env ]; then
  # shellcheck disable=SC1091
  set -a; . ./backend/.env; set +a
fi
DB_NAME="${POSTGRES_DB:-esports_db}"
DB_USER="${POSTGRES_USER:-esports_user}"

TARGET="${1:-}"
if [ "$TARGET" = "--latest" ]; then
  TARGET=$(ls -1t "${BACKUP_DIR}"/${DB_NAME}-*.sql.gz 2>/dev/null | head -1 || true)
fi
if [ -z "$TARGET" ] || [ ! -f "$TARGET" ]; then
  echo "使い方: $0 <バックアップファイル> | --latest"
  echo
  echo "利用可能なバックアップ:"
  ls -1t "${BACKUP_DIR}"/${DB_NAME}-*.sql.gz 2>/dev/null | head -10 || echo "  (なし)"
  exit 1
fi

echo "リストア対象: $TARGET"
echo "対象DB      : $DB_NAME"
echo
echo "!! 現在のデータベースの内容は失われます !!"
read -r -p "続行するには 'yes' と入力してください: " CONFIRM
[ "$CONFIRM" = "yes" ] || { echo "中止しました"; exit 1; }

# 書き込みを止めてから流し込む（アプリが接続したままだと復元が競合する）
echo "アプリを停止しています..."
$COMPOSE stop api worker scheduler >/dev/null

echo "リストア中..."
gzip -dc "$TARGET" | $COMPOSE exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 >/dev/null

echo "アプリを再開しています..."
$COMPOSE start api worker scheduler >/dev/null

echo "完了しました"
