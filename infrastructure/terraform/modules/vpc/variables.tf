variable "project" {
  description = "Project name (used as a prefix for all resource names)"
  type        = string
}

variable "environment" {
  description = "Deployment environment: demo | mvp | prod"
  type        = string
}

variable "aws_region" {
  description = "AWS region to deploy resources into"
  type        = string
  default     = "ap-northeast-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (one per AZ). Empty list disables private subnets."
  type        = list(string)
  default     = []
}

variable "availability_zones" {
  description = "Availability zones to use (must match the count of subnet CIDRs)"
  type        = list(string)
  default     = ["ap-northeast-1a", "ap-northeast-1c"]
}

variable "create_nat_gateway" {
  description = "Create a NAT Gateway for private subnets (~$32/month). Set false for demo."
  type        = bool
  default     = false
}

variable "admin_ssh_cidrs" {
  description = "CIDR blocks allowed SSH access to EC2. Add your home/office IP."
  type        = list(string)
  default     = []
}
