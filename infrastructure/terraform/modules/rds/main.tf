locals {
  name_prefix = "${var.project}-${var.environment}"
  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_db_subnet_group" "this" {
  name        = "${local.name_prefix}-db-subnet-group"
  subnet_ids  = var.subnet_ids
  description = "Subnet group for ${local.name_prefix} RDS instance"

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-db-subnet-group" })
}

resource "aws_db_parameter_group" "postgres15" {
  name        = "${local.name_prefix}-pg15"
  family      = "postgres15"
  description = "Custom parameter group for ${local.name_prefix}"

  # WAL level = logical enables Debezium CDC for future data lake integration
  parameter {
    name  = "wal_level"
    value = "logical"
  }

  # Lower random_page_cost for SSD storage (RDS uses SSD by default)
  parameter {
    name  = "random_page_cost"
    value = "1.1"
  }

  # Allow up to 200 connections (managed by asyncpg connection pool)
  parameter {
    name  = "max_connections"
    value = "200"
  }

  # Kill idle-in-transaction sessions after 30 s to prevent lock buildup
  parameter {
    name  = "idle_in_transaction_session_timeout"
    value = "30000"
  }

  # Enable pg_stat_statements for query performance analysis
  parameter {
    name         = "shared_preload_libraries"
    value        = "pg_stat_statements"
    apply_method = "pending-reboot"
  }

  tags = local.common_tags
}

resource "aws_db_instance" "postgres" {
  identifier        = "${local.name_prefix}-postgres"
  engine            = "postgres"
  engine_version    = "15.7"
  instance_class    = var.instance_class
  allocated_storage = var.allocated_storage

  max_allocated_storage = var.max_allocated_storage > 0 ? var.max_allocated_storage : null

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [var.sg_rds_id]
  parameter_group_name   = aws_db_parameter_group.postgres15.name

  multi_az               = var.multi_az
  publicly_accessible    = false  # always false — access via EC2/ECS only
  storage_type           = "gp2"
  storage_encrypted      = true

  backup_retention_period = var.backup_retention_days
  backup_window           = "03:00-04:00"  # 03:00 UTC (after ETL export, before aggregation)
  maintenance_window      = "Mon:04:00-Mon:05:00"

  deletion_protection          = var.deletion_protection
  skip_final_snapshot          = !var.deletion_protection
  final_snapshot_identifier    = var.deletion_protection ? "${local.name_prefix}-final-snapshot" : null

  performance_insights_enabled          = var.performance_insights_enabled
  performance_insights_retention_period = var.performance_insights_enabled ? 7 : null

  # CloudWatch log exports
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-postgres" })

  lifecycle {
    # Prevent Terraform from destroying the DB if the password changes in tfvars.
    # Use AWS console or aws-cli to rotate passwords in production.
    ignore_changes = [password]
  }
}

# CloudWatch alarm: high CPU on RDS
resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${local.name_prefix}-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS CPU utilization above 80%"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres.id
  }

  tags = local.common_tags
}
