#!/usr/bin/env bash
#
# 稼働状況の定期点検。異常があれば Discord Webhook へ通知する。
#
# 無料枠VMで実際に起きるのは「ディスクが埋まって書き込めなくなる」
# 「コンテナが落ちたまま気付かない」「証明書が切れる」の3つ。
# 監視基盤を持たない前提で、この3点だけを cron で見る。
#
# cron 例（15分ごと）:
#   */15 * * * * /opt/app/scripts/healthcheck.sh >> /var/log/axelia-health.log 2>&1
#
# 通知先は backend/.env の HEALTHCHECK_WEBHOOK_URL（未設定なら標準出力のみ）。
set -uo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
COMPOSE="${COMPOSE_CMD:-docker compose}"
DISK_THRESHOLD="${DISK_THRESHOLD:-80}"
CERT_WARN_DAYS="${CERT_WARN_DAYS:-14}"

cd "$APP_DIR"
if [ -f backend/.env ]; then
  # shellcheck disable=SC1091
  set -a; . ./backend/.env; set +a
fi

PROBLEMS=()

# ── 1. ディスク使用率 ───────────────────────────────────────────────────────
DISK_PCT=$(df -P "$APP_DIR" | awk 'NR==2 {gsub("%",""); print $5}')
if [ "${DISK_PCT:-0}" -ge "$DISK_THRESHOLD" ]; then
  PROBLEMS+=("ディスク使用率 ${DISK_PCT}%（閾値 ${DISK_THRESHOLD}%）")
fi

# ── 2. コンテナの稼働状態 ───────────────────────────────────────────────────
EXPECTED="nginx frontend api worker scheduler postgres redis"
for svc in $EXPECTED; do
  state=$($COMPOSE ps --format '{{.Service}} {{.State}}' 2>/dev/null | awk -v s="$svc" '$1==s {print $2}')
  if [ "$state" != "running" ]; then
    PROBLEMS+=("${svc} が起動していません (state=${state:-なし})")
  fi
done

# ── 3. API の応答 ───────────────────────────────────────────────────────────
if ! $COMPOSE exec -T api python -c "
import urllib.request,sys
try:
    urllib.request.urlopen('http://localhost:8000/health', timeout=5)
except Exception as e:
    sys.exit(1)
" >/dev/null 2>&1; then
  PROBLEMS+=("API のヘルスチェックに失敗")
fi

# ── 4. TLS 証明書の残り日数 ─────────────────────────────────────────────────
CERT=$(ls -1 /etc/letsencrypt/live/*/fullchain.pem 2>/dev/null | head -1)
if [ -n "$CERT" ]; then
  END=$(openssl x509 -enddate -noout -in "$CERT" 2>/dev/null | cut -d= -f2)
  if [ -n "$END" ]; then
    LEFT=$(( ( $(date -d "$END" +%s) - $(date +%s) ) / 86400 ))
    if [ "$LEFT" -le "$CERT_WARN_DAYS" ]; then
      PROBLEMS+=("TLS証明書の残り ${LEFT}日（自動更新を確認してください）")
    fi
  fi
fi

# ── 5. バックアップの鮮度 ───────────────────────────────────────────────────
LATEST=$(ls -1t "${APP_DIR}/backups"/*.sql.gz 2>/dev/null | head -1)
if [ -z "$LATEST" ]; then
  PROBLEMS+=("バックアップが1件もありません")
elif [ "$(( ( $(date +%s) - $(date -r "$LATEST" +%s) ) / 3600 ))" -gt 30 ]; then
  PROBLEMS+=("直近のバックアップが30時間以上前です（$(basename "$LATEST")）")
fi

# ── 結果 ────────────────────────────────────────────────────────────────────
TS="$(date -u +%FT%TZ)"
if [ ${#PROBLEMS[@]} -eq 0 ]; then
  echo "[$TS] 正常（ディスク ${DISK_PCT}%）"
  exit 0
fi

MESSAGE="AXELIA 稼働点検で問題を検出しました（${TS}）"
for p in "${PROBLEMS[@]}"; do
  echo "[$TS] 異常: $p"
  MESSAGE="${MESSAGE}\n・${p}"
done

if [ -n "${HEALTHCHECK_WEBHOOK_URL:-}" ]; then
  curl -fsS -X POST -H "Content-Type: application/json" \
    -d "{\"content\": \"$(printf '%b' "$MESSAGE" | sed 's/"/\\"/g' | sed ':a;N;$!ba;s/\n/\n/g')\"}" \
    "$HEALTHCHECK_WEBHOOK_URL" >/dev/null && echo "[$TS] Discord へ通知しました"
fi
exit 1
