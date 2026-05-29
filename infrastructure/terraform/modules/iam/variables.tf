variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "s3_bucket_arn" {
  description = "ARN of the analytics S3 bucket (grants r/w access to EC2/ECS)"
  type        = string
}

variable "sqs_queue_arns" {
  description = "ARNs of SQS queues the application needs to send/receive from"
  type        = list(string)
  default     = []
}
