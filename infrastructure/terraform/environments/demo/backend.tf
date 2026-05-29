# Remote state stored in S3 so teammates can share Terraform state.
# For a solo demo, you can comment this block out and use local state instead.
#
# Bootstrap:
#   aws s3 mb s3://esports-platform-tfstate-demo --region ap-northeast-1
#   aws dynamodb create-table \
#     --table-name esports-platform-tflock-demo \
#     --attribute-definitions AttributeName=LockID,AttributeType=S \
#     --key-schema AttributeName=LockID,KeyType=HASH \
#     --billing-mode PAY_PER_REQUEST \
#     --region ap-northeast-1

terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket       = "esports-platform-tfstate-demo"
    key          = "demo/terraform.tfstate"
    region       = "ap-northeast-1"
    use_lockfile = true
    encrypt      = true
    profile      = "terraform-deploy"
  }
}

provider "aws" {
  region  = var.aws_region
  profile = "terraform-deploy"

  default_tags {
    tags = {
      Project     = var.project
      Environment = "demo"
      ManagedBy   = "terraform"
    }
  }
}
