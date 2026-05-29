locals {
  name_prefix = "${var.project}-${var.environment}"
  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
  use_https = var.acm_certificate_arn != ""
}

resource "aws_cloudfront_distribution" "this" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${local.name_prefix} distribution"
  price_class         = var.price_class
  aliases             = var.aliases
  http_version        = "http2and3"
  wait_for_deployment = false

  # ── Default origin: EC2 Nginx (all routes) ───────────────────────────────
  origin {
    origin_id   = "ec2-nginx"
    domain_name = var.origin_domain_name

    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_protocol_policy   = "http-only"  # Nginx on EC2 handles SSL termination
      origin_ssl_protocols     = ["TLSv1.2"]
      origin_read_timeout      = 60
      origin_keepalive_timeout = 60
    }
  }

  # ── Default cache behaviour (proxies everything to Nginx) ────────────────
  default_cache_behavior {
    target_origin_id       = "ec2-nginx"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]

    # Disable default caching for API responses (Cache-Control headers take precedence)
    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Origin", "Host"]
      cookies {
        forward = "all"
      }
    }

    default_ttl = var.default_ttl
    min_ttl     = 0
    max_ttl     = 86400
    compress    = true
  }

  # ── /api/* — no caching (pass-through) ───────────────────────────────────
  ordered_cache_behavior {
    path_pattern           = "/api/*"
    target_origin_id       = "ec2-nginx"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]

    forwarded_values {
      query_string = true
      headers      = ["*"]
      cookies { forward = "all" }
    }

    default_ttl = 0
    min_ttl     = 0
    max_ttl     = 0
    compress    = false
  }

  # ── SSL viewer certificate ────────────────────────────────────────────────
  dynamic "viewer_certificate" {
    for_each = local.use_https ? [1] : []
    content {
      acm_certificate_arn      = var.acm_certificate_arn
      ssl_support_method       = "sni-only"
      minimum_protocol_version = "TLSv1.2_2021"
    }
  }

  dynamic "viewer_certificate" {
    for_each = local.use_https ? [] : [1]
    content {
      cloudfront_default_certificate = true
    }
  }

  # ── Geo restrictions: none ────────────────────────────────────────────────
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # ── Access logging (optional) ─────────────────────────────────────────────
  dynamic "logging_config" {
    for_each = var.s3_logs_bucket != "" ? [1] : []
    content {
      include_cookies = false
      bucket          = var.s3_logs_bucket
      prefix          = "cloudfront/"
    }
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-cf" })
}
