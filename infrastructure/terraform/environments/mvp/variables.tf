variable "project" {
  type    = string
  default = "esports-platform"
}

variable "aws_region" {
  type    = string
  default = "ap-northeast-1"
}

variable "admin_ssh_cidrs" {
  type    = list(string)
  default = []
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "secret_key" {
  type      = string
  sensitive = true
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN in the SAME region as the ALB (ap-northeast-1)"
  type        = string
}

variable "acm_certificate_arn_us_east_1" {
  description = "ACM certificate ARN in us-east-1 for CloudFront"
  type        = string
}

variable "custom_domain_aliases" {
  type    = list(string)
  default = []
}

variable "discord_webhook_url" {
  type      = string
  sensitive = true
  default   = ""
}

variable "api_image" {
  description = "Full GHCR/ECR URI for the API image (e.g. ghcr.io/org/esports-api:sha-abc)"
  type        = string
}

variable "frontend_image" {
  type = string
}

variable "worker_image" {
  type = string
}

variable "api_desired_count" {
  type    = number
  default = 2
}
