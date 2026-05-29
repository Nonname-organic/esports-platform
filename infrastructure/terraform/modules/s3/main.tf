locals {
  name_prefix = "${var.project}-${var.environment}"
  bucket_name = "${local.name_prefix}-${var.bucket_suffix}"
  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket" "analytics" {
  bucket        = local.bucket_name
  force_destroy = var.force_destroy

  tags = merge(local.common_tags, { Name = local.bucket_name })
}

resource "aws_s3_bucket_versioning" "analytics" {
  bucket = aws_s3_bucket.analytics.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "analytics" {
  bucket = aws_s3_bucket.analytics.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "analytics" {
  bucket = aws_s3_bucket.analytics.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle: raw NDJSON → Glacier Instant Retrieval → expire
resource "aws_s3_bucket_lifecycle_configuration" "analytics" {
  bucket = aws_s3_bucket.analytics.id

  rule {
    id     = "raw-analytics-retention"
    status = "Enabled"

    filter {
      prefix = "analytics/raw/"
    }

    transition {
      days          = var.glacier_transition_days
      storage_class = "GLACIER_IR"
    }

    expiration {
      days = var.raw_event_retention_days + var.glacier_transition_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  # Media uploads (team logos, avatars)
  rule {
    id     = "media-uploads-retention"
    status = "Enabled"

    filter {
      prefix = "media/"
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}
