variable "project" { type = string }
variable "environment" { type = string }

variable "subnet_id" {
  description = "Public subnet to launch the EC2 instance into"
  type        = string
}

variable "sg_ec2_id" { type = string }
variable "instance_profile_name" { type = string }

variable "instance_type" {
  description = "EC2 instance type. t2.micro is free-tier eligible for 12 months."
  type        = string
  default     = "t2.micro"
}

variable "key_name" {
  description = "Name of an existing EC2 key pair for SSH access"
  type        = string
}

variable "ami_id" {
  description = "Amazon Machine Image ID. Defaults to Amazon Linux 2023 in ap-northeast-1."
  type        = string
  default     = "ami-0b5c74e235ed808b9"  # Amazon Linux 2023 ap-northeast-1
}

variable "root_volume_size_gb" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 20
}

variable "swap_size_gb" {
  description = "Swap file size created by user_data script. Recommended for t2.micro (1GB RAM)."
  type        = number
  default     = 1
}

variable "app_repo_url" {
  description = "Git repository URL to clone on first boot (HTTPS)"
  type        = string
  default     = ""
}

variable "ghcr_image_tag" {
  description = "Container image tag to deploy (e.g. sha-abc1234 or latest)"
  type        = string
  default     = "latest"
}

# Environment variables injected into /opt/app/.env on the instance
variable "app_env" {
  description = "Map of environment variable key-value pairs written to /opt/app/.env"
  type        = map(string)
  sensitive   = true
  default     = {}
}
