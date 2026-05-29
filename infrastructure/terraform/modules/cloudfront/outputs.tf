output "distribution_id" {
  value = aws_cloudfront_distribution.this.id
}

output "domain_name" {
  description = "CloudFront distribution domain (*.cloudfront.net)"
  value       = aws_cloudfront_distribution.this.domain_name
}

output "hosted_zone_id" {
  description = "CloudFront hosted zone ID (for Route53 alias records)"
  value       = aws_cloudfront_distribution.this.hosted_zone_id
}
