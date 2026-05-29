terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "esports-platform-tfstate-mvp"
    key            = "mvp/terraform.tfstate"
    region         = "ap-northeast-1"
    dynamodb_table = "esports-platform-tflock-mvp"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project
      Environment = "mvp"
      ManagedBy   = "terraform"
    }
  }
}
