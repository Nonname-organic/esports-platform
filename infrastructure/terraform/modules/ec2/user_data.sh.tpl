#!/bin/bash
set -e

# ── Swap (critical for t2.micro with 1GB RAM) ─────────────────────────────────
if [ ! -f /swapfile ]; then
  fallocate -l ${swap_size_gb}G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# ── Docker ─────────────────────────────────────────────────────────────────────
yum update -y
yum install -y docker git
systemctl enable --now docker
usermod -aG docker ec2-user

# Docker Compose v2 plugin
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# ── Application directory ──────────────────────────────────────────────────────
mkdir -p /opt/app
chown ec2-user:ec2-user /opt/app

%{ if app_repo_url != "" ~}
# Clone repo on first boot
su - ec2-user -c "git clone ${app_repo_url} /opt/app/esports-platform"
%{ endif ~}

# Write environment file from Terraform variables
cat > /opt/app/.env <<'ENVEOF'
${env_file_content}
ENVEOF
chmod 600 /opt/app/.env
chown ec2-user:ec2-user /opt/app/.env

# ── CloudWatch Agent ───────────────────────────────────────────────────────────
yum install -y amazon-cloudwatch-agent

cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json <<'CWEOF'
{
  "agent": { "metrics_collection_interval": 60 },
  "metrics": {
    "namespace": "EsportsPlatform/EC2",
    "metrics_collected": {
      "mem":  { "measurement": ["mem_used_percent"] },
      "disk": { "measurement": ["disk_used_percent"], "resources": ["/"] },
      "swap": { "measurement": ["swap_used_percent"] }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/opt/app/logs/api.log",
            "log_group_name": "/esports-platform/api",
            "log_stream_name": "{instance_id}",
            "retention_in_days": 30
          },
          {
            "file_path": "/var/log/nginx/access.log",
            "log_group_name": "/esports-platform/nginx",
            "log_stream_name": "{instance_id}",
            "retention_in_days": 14
          }
        ]
      }
    }
  }
}
CWEOF

/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
  -s
