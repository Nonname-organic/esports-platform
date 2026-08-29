#!/usr/bin/env bash
#
# Oracle Cloud VM 上での初期構築（deploy-to-vm.sh から自動実行される）。
# 冪等: 2回目以降の実行は更新デプロイとして機能する。
#
#   sudo bash /opt/app/scripts/vm-bootstrap.sh
set -euo pipefail

DOMAIN="demo.axelia-esports.jp"
APP_DIR="/opt/app"
CERT_EMAIL="axelia.esports@gmail.com"

cd "$APP_DIR"

echo "── 1/6 Docker ─────────────────────────────────"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

echo "── 2/6 OS内ファイアウォール開放 ───────────────"
# Oracle Ubuntu イメージは REJECT ルールが先頭にあるため、セキュリティリスト
# だけ開けても届かない（phase10 のハマりポイント）
for port in 80 443; do
  if ! iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null; then
    iptables -I INPUT 5 -p tcp --dport "$port" -j ACCEPT
  fi
done
command -v netfilter-persistent >/dev/null 2>&1 && netfilter-persistent save || true

echo "── 3/6 HTTP で起動（証明書取得の前段） ────────"
mkdir -p certbot-www nginx/ssl backups
docker compose -f docker-compose.yml -f docker-compose.oracle.yml up -d --build

echo "── 4/6 TLS証明書 ──────────────────────────────"
if [ ! -d "/etc/letsencrypt/live/${DOMAIN}" ]; then
  command -v certbot >/dev/null 2>&1 || { apt-get update -qq && apt-get install -y -qq certbot; }
  certbot certonly --webroot -w "${APP_DIR}/certbot-www" -d "$DOMAIN" \
    --email "$CERT_EMAIL" --agree-tos --non-interactive
  # 更新後に nginx を自動リロード
  mkdir -p /etc/letsencrypt/renewal-hooks/deploy
  cat > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh <<'HOOK'
#!/bin/sh
cd /opt/app && docker compose exec -T nginx nginx -s reload
HOOK
  chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
fi

echo "── 5/6 TLS 構成で再起動 ───────────────────────"
docker compose -f docker-compose.yml -f docker-compose.tls.yml -f docker-compose.oracle.yml up -d --build
sleep 10
docker compose exec -T api alembic upgrade head

echo "── 6/6 DBリストア（初回のみ） ─────────────────"
LATEST=$(ls -1t backups/*.sql.gz 2>/dev/null | head -1 || true)
TOURNAMENTS=$(docker compose exec -T postgres psql -U esports_user -d esports_db -t -A \
  -c "SELECT count(*) FROM tournaments;" 2>/dev/null || echo 0)
if [ -n "$LATEST" ] && [ "${TOURNAMENTS:-0}" = "0" ]; then
  echo "  ${LATEST} を復元します"
  docker compose stop api worker scheduler >/dev/null
  gzip -dc "$LATEST" | docker compose exec -T postgres psql -U esports_user -d esports_db -v ON_ERROR_STOP=1 >/dev/null
  docker compose start api worker scheduler >/dev/null
else
  echo "  スキップ（既存データあり または バックアップなし）"
fi

echo "── 運用ジョブ登録 ─────────────────────────────"
bash "${APP_DIR}/scripts/install-ops-cron.sh" || true

echo
echo "完了: https://${DOMAIN}"
