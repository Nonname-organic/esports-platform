locals {
  name_prefix = "${var.project}-${var.environment}"
  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  # Render .env file from app_env map
  env_file_content = join("\n", [
    for k, v in var.app_env : "${k}=${v}"
  ])
}

resource "aws_instance" "app" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [var.sg_ec2_id]
  iam_instance_profile   = var.instance_profile_name
  key_name               = var.key_name

  root_block_device {
    volume_type           = "gp2"
    volume_size           = var.root_volume_size_gb
    delete_on_termination = true
    encrypted             = true
  }

  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    swap_size_gb     = var.swap_size_gb
    app_repo_url     = var.app_repo_url
    ghcr_image_tag   = var.ghcr_image_tag
    env_file_content = local.env_file_content
  })

  # Replace instance on user_data changes (rolling deploy for demo)
  user_data_replace_on_change = false  # keep false to avoid accidental replacement

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-app" })

  lifecycle {
    # Prevent Terraform from replacing the instance just because the AMI changed.
    # Use the deployment workflow instead.
    ignore_changes = [ami, user_data]
  }
}

resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-app-eip" })

  # EIP depends on IGW existing (Terraform doesn't infer this automatically)
  depends_on = [aws_instance.app]
}

# CloudWatch alarm: EC2 CPU high
resource "aws_cloudwatch_metric_alarm" "ec2_cpu" {
  alarm_name          = "${local.name_prefix}-ec2-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "EC2 CPU above 80% for 10 min"
  treat_missing_data  = "notBreaching"

  dimensions = {
    InstanceId = aws_instance.app.id
  }

  tags = local.common_tags
}
