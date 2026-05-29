# ============================================================================
# Demo Environment — AWS Free Tier
#
# Architecture:
#   CloudFront → EC2 t2.micro (Nginx + Docker Compose)
#                  ├── Next.js  :3000
#                  ├── FastAPI  :8000
#                  ├── Worker   (no port)
#                  └── Redis    :6379 (Docker, ephemeral)
#            └── RDS db.t3.micro (PostgreSQL 15, Single-AZ)
#            └── SQS  (3 queues + DLQs)
#            └── S3   (analytics exports)
#
# Cost: ~$0.50/month (Route53 only; all else is free tier)
# ============================================================================

locals {
  environment = "demo"
}

# ── VPC ───────────────────────────────────────────────────────────────────────
module "vpc" {
  source = "../../modules/vpc"

  project     = var.project
  environment = local.environment
  aws_region  = var.aws_region

  # Demo: public subnets only. No NAT Gateway ($32/month saved).
  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnet_cidrs = []
  create_nat_gateway   = false

  admin_ssh_cidrs = var.admin_ssh_cidrs
}

# ── S3 (analytics NDJSON exports) ────────────────────────────────────────────
module "s3" {
  source = "../../modules/s3"

  project       = var.project
  environment   = local.environment
  force_destroy = true  # safe to destroy in demo
}

# ── SQS ───────────────────────────────────────────────────────────────────────
module "sqs" {
  source = "../../modules/sqs"

  project     = var.project
  environment = local.environment
}

# ── IAM (EC2 instance profile) ────────────────────────────────────────────────
module "iam" {
  source = "../../modules/iam"

  project        = var.project
  environment    = local.environment
  s3_bucket_arn  = module.s3.bucket_arn
  sqs_queue_arns = module.sqs.all_queue_arns
}

# ── RDS (PostgreSQL 15, db.t3.micro, Single-AZ) ───────────────────────────────
module "rds" {
  source = "../../modules/rds"

  project     = var.project
  environment = local.environment

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.public_subnet_ids  # public subnet for demo (no NAT)
  sg_rds_id  = module.vpc.sg_rds_id

  instance_class    = "db.t3.micro"  # free tier
  allocated_storage = 20             # free tier max
  multi_az          = false          # free tier (Multi-AZ doubles cost)
  db_password       = var.db_password

  backup_retention_days        = 1
  deletion_protection          = false
  performance_insights_enabled = false
}

# ── EC2 (t2.micro, Docker Compose) ────────────────────────────────────────────
module "ec2" {
  source = "../../modules/ec2"

  project     = var.project
  environment = local.environment

  subnet_id             = module.vpc.public_subnet_ids[0]
  sg_ec2_id             = module.vpc.sg_ec2_id
  instance_profile_name = module.iam.ec2_instance_profile_name
  key_name              = var.ec2_key_name
  instance_type         = "t3.micro"
  ghcr_image_tag        = var.ghcr_image_tag

  # Application environment variables written to /opt/app/.env on first boot.
  # Sensitive values come from terraform.tfvars (never commit that file).
  app_env = {
    ENVIRONMENT = "demo"
    DEBUG       = "false"

    SECRET_KEY                   = var.secret_key
    ACCESS_TOKEN_EXPIRE_MINUTES  = "60"
    REFRESH_TOKEN_EXPIRE_DAYS    = "7"

    DB_HOST     = module.rds.host
    DB_PORT     = tostring(module.rds.port)
    DB_NAME     = module.rds.db_name
    DB_USER     = "esports_user"
    DB_PASSWORD = var.db_password

    REDIS_HOST = "localhost"  # Docker container on same EC2 host
    REDIS_PORT = "6379"
    REDIS_DB   = "0"

    AWS_REGION                = var.aws_region
    S3_BUCKET_NAME            = module.s3.bucket_id
    SQS_MATCH_QUEUE_URL       = module.sqs.queue_urls["match"]
    SQS_NOTIFICATION_QUEUE_URL = module.sqs.queue_urls["notification"]
    SQS_ANALYTICS_QUEUE_URL   = module.sqs.queue_urls["analytics"]

    DISCORD_WEBHOOK_URL = var.discord_webhook_url

    ALLOWED_ORIGINS = length(var.custom_domain_aliases) > 0 ? join(",", [
      for alias in var.custom_domain_aliases : "https://${alias}"
    ]) : "*"

    NEXT_PUBLIC_API_URL = length(var.custom_domain_aliases) > 0 ? (
      "https://${var.custom_domain_aliases[0]}/api/v1"
    ) : "/api/v1"
  }
}

# ── CloudFront ────────────────────────────────────────────────────────────────
module "cloudfront" {
  source = "../../modules/cloudfront"

  project     = var.project
  environment = local.environment

  origin_domain_name  = module.ec2.public_dns
  acm_certificate_arn = var.acm_certificate_arn
  aliases             = var.custom_domain_aliases
  price_class         = "PriceClass_100"
  default_ttl         = 300
}
