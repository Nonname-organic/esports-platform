# ============================================================================
# MVP Environment — ECS Fargate + RDS Multi-AZ + ALB
#
# Architecture:
#   CloudFront → ALB (HTTPS) → ECS Fargate (private subnets)
#                                ├── API tasks  ×2 (auto-scales to 6)
#                                ├── Frontend ×1
#                                └── Worker ×1
#                              RDS db.t3.medium (Multi-AZ)
#                              ElastiCache t3.micro (Redis)
#                              SQS + S3 (same as demo)
#
# Cost: ~$185/month
#   ALB: ~$20  |  ECS Fargate: ~$60  |  RDS Multi-AZ: ~$50
#   ElastiCache: ~$25  |  NAT Gateway: ~$32
# ============================================================================

locals {
  environment = "mvp"
}

# ── VPC (public + private, NAT Gateway) ───────────────────────────────────────
module "vpc" {
  source = "../../modules/vpc"

  project     = var.project
  environment = local.environment
  aws_region  = var.aws_region

  public_subnet_cidrs  = ["10.1.1.0/24", "10.1.2.0/24"]
  private_subnet_cidrs = ["10.1.11.0/24", "10.1.12.0/24"]
  create_nat_gateway   = true  # required for Fargate in private subnets

  admin_ssh_cidrs = var.admin_ssh_cidrs
}

# ── S3 ─────────────────────────────────────────────────────────────────────────
module "s3" {
  source = "../../modules/s3"

  project       = var.project
  environment   = local.environment
  force_destroy = false  # protect data in MVP
}

# ── SQS ───────────────────────────────────────────────────────────────────────
module "sqs" {
  source = "../../modules/sqs"

  project     = var.project
  environment = local.environment
}

# ── IAM ───────────────────────────────────────────────────────────────────────
module "iam" {
  source = "../../modules/iam"

  project        = var.project
  environment    = local.environment
  s3_bucket_arn  = module.s3.bucket_arn
  sqs_queue_arns = module.sqs.all_queue_arns
}

# ── RDS (db.t3.medium, Multi-AZ) ──────────────────────────────────────────────
module "rds" {
  source = "../../modules/rds"

  project     = var.project
  environment = local.environment

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids  # private subnets for MVP
  sg_rds_id  = module.vpc.sg_rds_id

  instance_class        = "db.t3.medium"
  allocated_storage     = 50
  max_allocated_storage = 200  # autoscale up to 200 GB
  multi_az              = true

  db_password                  = var.db_password
  backup_retention_days        = 7
  deletion_protection          = true
  performance_insights_enabled = true
}

# ── ElastiCache Redis (replaces Docker Redis in demo) ─────────────────────────
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.project}-mvp-redis-subnet"
  subnet_ids = module.vpc.private_subnet_ids
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${var.project}-mvp-redis"
  engine               = "redis"
  engine_version       = "7.1"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [module.vpc.sg_redis_id]
  port                 = 6379

  tags = {
    Project     = var.project
    Environment = local.environment
    ManagedBy   = "terraform"
  }
}

# ── ALB ───────────────────────────────────────────────────────────────────────
# ALB needs its own security group (open 80/443 from internet)
resource "aws_security_group" "alb" {
  name        = "${var.project}-mvp-sg-alb"
  description = "ALB public ingress"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Project     = var.project
    Environment = local.environment
    ManagedBy   = "terraform"
  }
}

module "alb" {
  source = "../../modules/alb"

  project             = var.project
  environment         = local.environment
  vpc_id              = module.vpc.vpc_id
  public_subnet_ids   = module.vpc.public_subnet_ids
  sg_alb_id           = aws_security_group.alb.id
  acm_certificate_arn = var.acm_certificate_arn
}

# ── ECS Fargate ────────────────────────────────────────────────────────────────
module "ecs" {
  source = "../../modules/ecs"

  project     = var.project
  environment = local.environment
  aws_region  = var.aws_region

  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  sg_app_id          = module.vpc.sg_ec2_id  # reuse app SG from VPC module

  alb_target_group_api_arn      = module.alb.target_group_api_arn
  alb_target_group_frontend_arn = module.alb.target_group_frontend_arn

  execution_role_arn = module.iam.ecs_execution_role_arn
  task_role_arn      = module.iam.ecs_task_role_arn

  ecr_api_image      = var.api_image
  ecr_frontend_image = var.frontend_image
  ecr_worker_image   = var.worker_image

  api_desired_count = var.api_desired_count

  app_env = {
    ENVIRONMENT = "mvp"
    DEBUG       = "false"

    SECRET_KEY                   = var.secret_key
    ACCESS_TOKEN_EXPIRE_MINUTES  = "15"
    REFRESH_TOKEN_EXPIRE_DAYS    = "7"

    DB_HOST     = module.rds.host
    DB_PORT     = tostring(module.rds.port)
    DB_NAME     = module.rds.db_name
    DB_USER     = "esports_user"
    DB_PASSWORD = var.db_password

    REDIS_HOST = aws_elasticache_cluster.redis.cache_nodes[0].address
    REDIS_PORT = "6379"
    REDIS_DB   = "0"

    AWS_REGION                 = var.aws_region
    S3_BUCKET_NAME             = module.s3.bucket_id
    SQS_MATCH_QUEUE_URL        = module.sqs.queue_urls["match"]
    SQS_NOTIFICATION_QUEUE_URL = module.sqs.queue_urls["notification"]
    SQS_ANALYTICS_QUEUE_URL    = module.sqs.queue_urls["analytics"]

    DISCORD_WEBHOOK_URL = var.discord_webhook_url

    ALLOWED_ORIGINS = length(var.custom_domain_aliases) > 0 ? join(",", [
      for alias in var.custom_domain_aliases : "https://${alias}"
    ]) : "https://${module.cloudfront.domain_name}"
  }
}

# ── CloudFront ────────────────────────────────────────────────────────────────
module "cloudfront" {
  source = "../../modules/cloudfront"

  project     = var.project
  environment = local.environment

  origin_domain_name  = module.alb.alb_dns_name
  acm_certificate_arn = var.acm_certificate_arn_us_east_1
  aliases             = var.custom_domain_aliases
  price_class         = "PriceClass_100"
}
