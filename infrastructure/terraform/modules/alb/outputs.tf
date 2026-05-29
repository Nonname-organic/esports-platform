output "alb_dns_name" {
  value = aws_lb.this.dns_name
}

output "alb_zone_id" {
  value = aws_lb.this.zone_id
}

output "target_group_api_arn" {
  value = aws_lb_target_group.api.arn
}

output "target_group_frontend_arn" {
  value = aws_lb_target_group.frontend.arn
}

output "https_listener_arn" {
  value = aws_lb_listener.https.arn
}
