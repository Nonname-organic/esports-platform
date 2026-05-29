variable "project" {
  type    = string
  default = "esports-platform"
}

variable "aws_region" {
  type    = string
  default = "ap-northeast-1"
}

variable "ec2_key_name" {
  description = "Name of an existing EC2 key pair to use for SSH"
  type        = string
}

variable "admin_ssh_cidrs" {
  description = "Your home/office IP in CIDR notation for SSH access (e.g. [\"203.0.113.1/32\"])"
  type        = list(string)
  default     = []
}

variable "db_password" {
  description = "RDS master password (store in environment variable TF_VAR_db_password)"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "FastAPI SECRET_KEY (at least 32 chars)"
  type        = string
  sensitive   = true
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN in us-east-1 for CloudFront (optional — leave empty to use default *.cloudfront.net)"
  type        = string
  default     = ""
}

variable "custom_domain_aliases" {
  description = "Custom domain aliases for CloudFront (requires acm_certificate_arn)"
  type        = list(string)
  default     = []
}

variable "discord_webhook_url" {
  description = "Discord webhook URL for notifications (optional)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "ghcr_image_tag" {
  description = "Container image tag deployed from CI"
  type        = string
  default     = "latest"
}
