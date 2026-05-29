output "bucket_id" {
  value = aws_s3_bucket.analytics.id
}

output "bucket_arn" {
  value = aws_s3_bucket.analytics.arn
}

output "bucket_domain_name" {
  value = aws_s3_bucket.analytics.bucket_domain_name
}
