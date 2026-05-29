variable "project" { type = string }
variable "environment" { type = string }

variable "message_retention_seconds" {
  description = "How long SQS retains unprocessed messages (default 4 days)"
  type        = number
  default     = 345600
}

variable "visibility_timeout_seconds" {
  description = "Visibility timeout for messages — must be > max worker processing time"
  type        = number
  default     = 120
}

variable "dlq_max_receive_count" {
  description = "Number of delivery attempts before a message is sent to the DLQ"
  type        = number
  default     = 3
}
