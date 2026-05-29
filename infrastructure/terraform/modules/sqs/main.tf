locals {
  name_prefix = "${var.project}-${var.environment}"
  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  # Queue definitions: name suffix → description
  queues = {
    match        = "Match result processing: ranking update + analytics aggregation"
    notification = "Async notification dispatch: Discord, in-app"
    analytics    = "Dedicated analytics stats update events (enriched with Riot API data)"
  }
}

# ── Dead Letter Queues (one per main queue) ───────────────────────────────────
resource "aws_sqs_queue" "dlq" {
  for_each = local.queues

  name                      = "${local.name_prefix}-${each.key}-dlq"
  message_retention_seconds = 1209600  # 14 days for DLQ (double main queue)

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-${each.key}-dlq"
    Purpose = "Dead letter queue for ${each.value}"
  })
}

# ── Main Queues ────────────────────────────────────────────────────────────────
resource "aws_sqs_queue" "main" {
  for_each = local.queues

  name                       = "${local.name_prefix}-${each.key}"
  message_retention_seconds  = var.message_retention_seconds
  visibility_timeout_seconds = var.visibility_timeout_seconds
  receive_wait_time_seconds  = 20  # long polling — reduces empty receives and cost

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[each.key].arn
    maxReceiveCount     = var.dlq_max_receive_count
  })

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-${each.key}"
    Purpose = each.value
  })
}

# ── CloudWatch Alarms: alert when DLQ depth > 0 ───────────────────────────────
resource "aws_cloudwatch_metric_alarm" "dlq_depth" {
  for_each = local.queues

  alarm_name          = "${local.name_prefix}-${each.key}-dlq-depth"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Messages stuck in DLQ for ${each.key} queue"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.dlq[each.key].name
  }

  tags = local.common_tags
}
