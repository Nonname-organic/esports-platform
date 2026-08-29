#!/usr/bin/env bash
#
# ローカル（Git Bash）から Oracle VM へデプロイする。
#
#   scripts/deploy-to-vm.sh ubuntu@<VMのIP> [SSH鍵のパス]
#
# やること:
#   1. ローカルの .env を本番値（demo.axelia-esports.jp）へパッチした .env.deploy を生成
#   2. コード一式 + 最新DBバックアップを tar で VM へ転送
#   3. VM 上で vm-bootstrap.sh を実行（Docker導入〜TLS〜起動〜リストアまで自動）
#
# 前提: VM は Ubuntu (ARM/x86どちらも可)、ポート80/443がセキュリティリストで開放済み、
#       DNS で demo.axelia-esports.jp が VM の IP を指していること（証明書取得に必要）
set -euo pipefail

TARGET="${1:-}"
KEY="${2:-}"
[ -n "$TARGET" ] || { echo "使い方: $0 ubuntu@<VMのIP> [SSH鍵パス]"; exit 1; }

SSH_OPTS=(-o StrictHostKeyChecking=accept-new)
[ -n "$KEY" ] && SSH_OPTS+=(-i "$KEY")

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

DOMAIN="demo.axelia-esports.jp"

echo "── 1/4 本番用 .env を生成 ─────────────────────"
[ -f backend/.env ] || { echo "backend/.env がありません"; exit 1; }
python - <<'PYEOF'
import pathlib, re
src = pathlib.Path("backend/.env").read_text(encoding="utf-8")
domain = "demo.axelia-esports.jp"
overrides = {
    "FRONTEND_BASE_URL": f"https://{domain}",
    "PUBLIC_WEB_URL": f"https://{domain}",
    "ALLOWED_ORIGINS": f"https://{domain}",
    "EXPOSE_API_DOCS": "false",
    "ENVIRONMENT": "demo",
    "USE_REDIS_QUEUE": "true",
}
lines = src.split("\n")
seen = set()
for i, line in enumerate(lines):
    key = line.split("=", 1)[0] if "=" in line and not line.startswith("#") else None
    if key in overrides:
        lines[i] = f"{key}={overrides[key]}"
        seen.add(key)
for key, value in overrides.items():
    if key not in seen:
        lines.append(f"{key}={value}")
pathlib.Path("backend/.env.deploy").write_text("\n".join(lines), encoding="utf-8")
print("  backend/.env.deploy を生成（本番URL・docs非公開・Redisキュー）")
PYEOF

echo "── 2/4 最新DBバックアップを用意 ───────────────"
bash scripts/backup-db.sh >/dev/null 2>&1 || echo "  警告: バックアップ取得に失敗（ローカルDB停止中?）"
LATEST_BACKUP=$(ls -1t backups/*.sql.gz 2>/dev/null | head -1 || true)
echo "  ${LATEST_BACKUP:-（なし: 空のDBで起動します）}"

echo "── 3/4 転送 ───────────────────────────────────"
TARBALL="$(mktemp -t axelia-deploy-XXXX.tar.gz)"
tar czf "$TARBALL" \
  --exclude=node_modules --exclude=.next --exclude=.git \
  --exclude=backups --exclude=backend/.env --exclude=certbot-www \
  --exclude=nginx/ssl --exclude="*.pyc" --exclude=__pycache__ \
  .
echo "  $(du -h "$TARBALL" | cut -f1) を転送します"
ssh "${SSH_OPTS[@]}" "$TARGET" "sudo mkdir -p /opt/app /opt/app/backups && sudo chown -R \$(whoami) /opt/app"
scp "${SSH_OPTS[@]}" "$TARBALL" "$TARGET:/tmp/axelia-deploy.tar.gz"
scp "${SSH_OPTS[@]}" backend/.env.deploy "$TARGET:/tmp/axelia.env"
[ -n "$LATEST_BACKUP" ] && scp "${SSH_OPTS[@]}" "$LATEST_BACKUP" "$TARGET:/opt/app/backups/"
rm -f "$TARBALL" backend/.env.deploy

echo "── 4/4 VM 上でセットアップ実行 ────────────────"
ssh "${SSH_OPTS[@]}" "$TARGET" "
  set -e
  tar xzf /tmp/axelia-deploy.tar.gz -C /opt/app
  mv /tmp/axelia.env /opt/app/backend/.env
  rm -f /tmp/axelia-deploy.tar.gz
  sudo bash /opt/app/scripts/vm-bootstrap.sh
"

echo
echo "デプロイ完了: https://${DOMAIN}"
