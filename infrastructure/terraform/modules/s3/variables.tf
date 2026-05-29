variable "project" { type = string }
variable "environment" { type = string }

variable "bucket_suffix" {
  description = "Appended to project-env to form the bucket name. Must be globally unique."
  type        = string
  default     = "analytics"
}

variable "raw_event_retention_days" {
  description = "Days to retain raw analytics_events NDJSON files in S3 before moving to Glacier"
  type        = number
  default     = 90
}

variable "glacier_transition_days" {
  description = "Days after which raw files transition to Glacier Instant Retrieval"
  type        = number
  default     = 365
}

variable "force_destroy" {
  description = "Allow terraform destroy to delete non-empty bucket. Set true only for demo/test."
  type        = bool
  default     = false
}
