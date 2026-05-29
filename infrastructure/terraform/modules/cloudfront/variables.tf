variable "project" { type = string }
variable "environment" { type = string }

variable "origin_domain_name" {
  description = "EC2 Elastic IP or ALB DNS name to proxy requests to"
  type        = string
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN (must be in us-east-1 for CloudFront)"
  type        = string
  default     = ""
}

variable "aliases" {
  description = "Custom domain aliases (e.g. [\"esports.example.com\"]). Requires acm_certificate_arn."
  type        = list(string)
  default     = []
}

variable "price_class" {
  description = "CloudFront price class. PriceClass_100 = cheapest (US/EU/JP)"
  type        = string
  default     = "PriceClass_100"
}

variable "default_ttl" {
  description = "Default TTL for cached objects in seconds"
  type        = number
  default     = 300
}

variable "s3_logs_bucket" {
  description = "S3 bucket domain name for CloudFront access logs. Empty = disabled."
  type        = string
  default     = ""
}
