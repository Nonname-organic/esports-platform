output "queue_urls" {
  description = "Map of queue name → URL"
  value = {
    for k, q in aws_sqs_queue.main : k => q.url
  }
}

output "queue_arns" {
  description = "Map of queue name → ARN"
  value = {
    for k, q in aws_sqs_queue.main : k => q.arn
  }
}

output "dlq_urls" {
  description = "Map of queue name → DLQ URL"
  value = {
    for k, q in aws_sqs_queue.dlq : k => q.url
  }
}

output "all_queue_arns" {
  description = "Flat list of all main queue ARNs (for IAM policy)"
  value       = [for q in aws_sqs_queue.main : q.arn]
}
