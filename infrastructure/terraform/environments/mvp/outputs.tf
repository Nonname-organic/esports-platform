output "cloudfront_domain" {
  value = "https://${module.cloudfront.domain_name}"
}

output "alb_dns_name" {
  value = module.alb.alb_dns_name
}

output "ecs_cluster_name" {
  value = module.ecs.cluster_name
}

output "rds_host" {
  value = module.rds.host
}

output "redis_host" {
  value = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "s3_bucket" {
  value = module.s3.bucket_id
}

output "sqs_urls" {
  value = module.sqs.queue_urls
}
