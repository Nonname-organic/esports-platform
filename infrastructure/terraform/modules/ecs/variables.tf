variable "project" { type = string }
variable "environment" { type = string }
variable "aws_region" { type = string }

variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "sg_app_id" { type = string }
variable "alb_target_group_api_arn" { type = string }
variable "alb_target_group_frontend_arn" { type = string }

variable "execution_role_arn" { type = string }
variable "task_role_arn" { type = string }

variable "ecr_api_image" {
  description = "Full ECR/GHCR image URI for the API container"
  type        = string
}

variable "ecr_frontend_image" {
  description = "Full ECR/GHCR image URI for the frontend container"
  type        = string
}

variable "ecr_worker_image" {
  description = "Full ECR/GHCR image URI for the worker container"
  type        = string
}

variable "api_cpu"      { type = number; default = 512 }
variable "api_memory"   { type = number; default = 1024 }
variable "frontend_cpu" { type = number; default = 256 }
variable "frontend_memory" { type = number; default = 512 }
variable "worker_cpu"   { type = number; default = 256 }
variable "worker_memory"{ type = number; default = 512 }

variable "api_desired_count"      { type = number; default = 2 }
variable "frontend_desired_count" { type = number; default = 1 }
variable "worker_desired_count"   { type = number; default = 1 }

variable "app_env" {
  description = "Environment variables for all containers"
  type        = map(string)
  sensitive   = true
  default     = {}
}

variable "log_retention_days" {
  type    = number
  default = 30
}
