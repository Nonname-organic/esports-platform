#!/usr/bin/env bash
#
# 本番VM（Oracle Cloud）で運用ジョブを cron に登録する。デプロイ後に1度だけ実行する。
#
#   sudo ./scripts/install-ops-cron.sh
#
# 登録されるもの:
#   - 毎日 03:15  DBバックアップ（14世代保持 / R2設定があれば同時アップロード）
#   - 15分ごと    稼働点検（ディスク・コンテナ・API・証明書・バックアップ鮮度）
#   - 毎週日曜    docker のイメージ・ボリューム掃除（ディスク逼迫の主因）
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
CRON_FILE="/etc/cron.d/axelia-ops"
LOG_DIR="/var/log"

if [ "$(id -u)" -ne 0 ]; then
  echo "root で実行してください: sudo $0"
  exit 1
fi

for s in backup-db.sh healthcheck.sh; do
  [ -x "${APP_DIR}/scripts/${s}" ] || { echo "見つかりません: ${APP_DIR}/scripts/${s}"; exit 1; }
done

cat > "$CRON_FILE" <<CRON
# AXELIA 運用ジョブ（scripts/install-ops-cron.sh が生成）
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# DBバックアップ（毎日 03:15 UTC）
15 3 * * * root ${APP_DIR}/scripts/backup-db.sh >> ${LOG_DIR}/axelia-backup.log 2>&1

# 稼働点検（15分ごと）
*/15 * * * * root ${APP_DIR}/scripts/healthcheck.sh >> ${LOG_DIR}/axelia-health.log 2>&1

# 未使用イメージ・ビルドキャッシュの掃除（毎週日曜 04:00 UTC）
0 4 * * 0 root docker system prune -af --filter "until=168h" >> ${LOG_DIR}/axelia-prune.log 2>&1
CRON

chmod 0644 "$CRON_FILE"

# ログの肥大化を防ぐ
cat > /etc/logrotate.d/axelia <<'ROTATE'
/var/log/axelia-*.log {
    weekly
    rotate 8
    compress
    missingok
    notifempty
    copytruncate
}
ROTATE

echo "登録しました: $CRON_FILE"
echo
echo "確認:"
echo "  systemctl status cron        … cron が動いているか"
echo "  tail -f /var/log/axelia-health.log"
echo
echo "証明書の自動更新も確認してください:"
echo "  systemctl list-timers | grep certbot"
echo "  certbot renew --dry-run"
