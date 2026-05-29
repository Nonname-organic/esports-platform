output "instance_id" {
  value = aws_instance.app.id
}

output "public_ip" {
  description = "Elastic IP address (stable across reboots)"
  value       = aws_eip.app.public_ip
}

output "public_dns" {
  description = "Elastic IP public DNS (for CloudFront origin)"
  value       = aws_eip.app.public_dns
}

output "private_ip" {
  value = aws_instance.app.private_ip
}
