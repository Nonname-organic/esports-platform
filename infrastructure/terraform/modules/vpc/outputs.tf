output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.this.id
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of private subnets (empty for demo)"
  value       = aws_subnet.private[*].id
}

output "sg_ec2_id" {
  description = "Security group ID for EC2 / ECS tasks"
  value       = aws_security_group.ec2.id
}

output "sg_rds_id" {
  description = "Security group ID for RDS"
  value       = aws_security_group.rds.id
}

output "sg_redis_id" {
  description = "Security group ID for ElastiCache"
  value       = aws_security_group.redis.id
}
