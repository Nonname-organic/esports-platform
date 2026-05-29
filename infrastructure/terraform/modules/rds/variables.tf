variable "project" { type = string }
variable "environment" { type = string }

variable "vpc_id" { type = string }
variable "subnet_ids" {
  description = "Subnet IDs for the DB subnet group (2+ AZs required)"
  type        = list(string)
}
variable "sg_rds_id" { type = string }

variable "instance_class" {
  description = "RDS instance class. db.t3.micro for demo (free tier), db.t3.medium for MVP"
  type        = string
  default     = "db.t3.micro"
}

variable "allocated_storage" {
  description = "Initial storage in GB. 20 is the free-tier max."
  type        = number
  default     = 20
}

variable "max_allocated_storage" {
  description = "Autoscaling ceiling in GB. 0 = disabled."
  type        = number
  default     = 0
}

variable "multi_az" {
  description = "Enable Multi-AZ for high availability. Doubles cost and disables free tier."
  type        = bool
  default     = false
}

variable "db_name" {
  type    = string
  default = "esports_db"
}

variable "db_username" {
  type    = string
  default = "esports_user"
}

variable "db_password" {
  description = "Master password. Use a strong random value — store in AWS Secrets Manager for production."
  type        = string
  sensitive   = true
}

variable "backup_retention_days" {
  description = "Days to retain automated backups. 0 disables backups (development only)."
  type        = number
  default     = 1
}

variable "deletion_protection" {
  description = "Prevent accidental deletion. Enable for production."
  type        = bool
  default     = false
}

variable "performance_insights_enabled" {
  description = "Enable Performance Insights (free for 7-day retention)"
  type        = bool
  default     = false
}
