# Discord Bot 用インフラ
# - SQS discord キュー（プラットフォーム → Bot のイベント連携）
# - SSM Parameter Store（Bot Token / OAuth Secret の秘匿管理）

variable "project" { type = string }
variable "environment" { type = string }

locals {
  name_prefix = "${var.project}-${var.environment}"
}

# ── SQS: Discord イベントキュー ────────────────────────────────────────────────
resource "aws_sqs_queue" "discord_dlq" {
  name                      = "${local.name_prefix}-discord-dlq"
  message_retention_seconds = 1209600 # 14日
  tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_sqs_queue" "discord" {
  name                       = "${local.name_prefix}-discord"
  visibility_timeout_seconds = 60
  receive_wait_time_seconds  = 20 # ロングポーリング
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.discord_dlq.arn
    maxReceiveCount     = 5
  })
  tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ── SSM: 秘匿パラメータ（値は手動 or CI/CDで設定） ─────────────────────────────
resource "aws_ssm_parameter" "discord_bot_token" {
  name  = "/${local.name_prefix}/discord/bot_token"
  type  = "SecureString"
  value = "PLACEHOLDER" # 実際の値はコンソール/CLIで上書き
  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "discord_client_secret" {
  name  = "/${local.name_prefix}/discord/client_secret"
  type  = "SecureString"
  value = "PLACEHOLDER"
  lifecycle {
    ignore_changes = [value]
  }
}

output "discord_queue_url" {
  value = aws_sqs_queue.discord.url
}

output "discord_queue_arn" {
  value = aws_sqs_queue.discord.arn
}
