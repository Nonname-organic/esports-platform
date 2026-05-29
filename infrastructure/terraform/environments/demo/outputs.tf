output "cloudfront_domain" {
  description = "Access the application at this URL (or your custom domain)"
  value       = "https://${module.cloudfront.domain_name}"
}

output "ec2_public_ip" {
  description = "EC2 Elastic IP — use for SSH and as CloudFront origin"
  value       = module.ec2.public_ip
}

output "ssh_command" {
  description = "SSH into the EC2 instance"
  value       = "ssh -i ~/.ssh/${var.ec2_key_name}.pem ec2-user@${module.ec2.public_ip}"
}

output "rds_host" {
  description = "RDS endpoint hostname"
  value       = module.rds.host
}

output "s3_bucket" {
  description = "Analytics S3 bucket name"
  value       = module.s3.bucket_id
}

output "sqs_urls" {
  description = "SQS queue URLs"
  value       = module.sqs.queue_urls
}
