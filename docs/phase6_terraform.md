# Phase 6 — Terraform Infrastructure as Code

## Directory Structure

```
infrastructure/terraform/
  modules/
    vpc/          VPC, subnets, IGW, NAT Gateway, Security Groups
    ec2/          EC2 instance, Elastic IP, CloudWatch alarm, user_data
    rds/          RDS PostgreSQL 15, parameter group, subnet group, CW alarm
    s3/           Analytics bucket, versioning, encryption, lifecycle rules
    sqs/          3 queues + DLQs + CW alarms (DLQ depth)
    cloudfront/   CloudFront distribution, viewer cert, path behaviours
    iam/          EC2 instance profile, ECS execution/task roles
    ecs/          ECS cluster, task definitions, services, auto-scaling
    alb/          ALB, target groups, HTTPS listener, path routing
  environments/
    demo/         AWS Free Tier — EC2 t2.micro + Docker Compose
    mvp/          ECS Fargate + RDS Multi-AZ + ALB + ElastiCache
```

## Environment Comparison

| Resource | Demo (~$0.50/mo) | MVP (~$185/mo) |
|----------|-----------------|----------------|
| Compute | EC2 t2.micro | ECS Fargate (API×2, Frontend×1, Worker×1) |
| Database | RDS db.t3.micro Single-AZ | RDS db.t3.medium Multi-AZ |
| Cache | Redis on Docker (ephemeral) | ElastiCache cache.t3.micro |
| Load Balancer | Nginx on EC2 | ALB (HTTPS, path routing) |
| Network | Public subnets only | Public + private subnets + NAT |
| Auto Scaling | None | ECS Service Auto Scaling (target CPU 70%) |
| Deletion Protection | false | true |

## Deployment Workflow

### Demo

```bash
cd infrastructure/terraform/environments/demo

# One-time: create backend S3 bucket + DynamoDB lock table
aws s3 mb s3://esports-platform-tfstate-demo --region ap-northeast-1
aws dynamodb create-table \
  --table-name esports-platform-tflock-demo \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

terraform init
terraform plan -out=tfplan
terraform apply tfplan

# After apply, SSH into EC2:
# ssh -i ~/.ssh/my-key.pem ec2-user@<ec2_public_ip>
# cd /opt/app/esports-platform
# docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### MVP

```bash
cd infrastructure/terraform/environments/mvp
# Same init/plan/apply flow
# Images are deployed by GitHub Actions (ECS rolling deploy)
```

## Key Design Decisions

### No NAT Gateway in Demo
NAT Gateway costs $32/month — more than the entire rest of the demo.  In the
demo environment EC2 and RDS both live in public subnets and are protected by
Security Groups.  The RDS `publicly_accessible = false` setting ensures that
even though it's in a public subnet, it has no public IP and is reachable only
from the EC2 security group.

### Separate SG for RDS
`sg-rds` has a single ingress rule: port 5432 from `sg-ec2` only.  No IP
ranges.  If the EC2 instance is terminated and a new one created in a different
AZ, the security group association still works because it's SG-to-SG, not
IP-to-IP.

### `ignore_changes = [task_definition, desired_count]` on ECS Services
GitHub Actions updates ECS task definitions on every deploy.  Without
`ignore_changes`, the next `terraform apply` would revert the service to
the task definition version in the `.tf` file.  This pattern delegates
image version management to CI while Terraform handles resource structure.

### S3 Lifecycle Policy
```
Raw NDJSON (analytics/raw/)
  Day 0–364:   S3 Standard  ($0.023/GB)
  Day 365+:    Glacier Instant Retrieval  ($0.004/GB)
  Day 455:     Expire (purge)
```
For a typical 10 MB/day raw event volume, the total S3 cost at steady state
is < $0.50/month.

### IAM Least Privilege
The EC2 instance profile and ECS task role have identical policies with three
permission sets:
- **S3**: scoped to the single analytics bucket ARN (not `*`)
- **SQS**: scoped to the three queue ARNs (not `*`)
- **CloudWatch/ECR**: requires `Resource: "*"` (AWS limitation)

### Remote State (S3 + DynamoDB)
State is stored in S3 with DynamoDB locking to prevent concurrent `apply`
races.  Each environment has its own bucket/key/lock table so that a demo
`destroy` cannot affect MVP state.

### Terraform `lifecycle.ignore_changes` on RDS password
Rotating the DB password via `terraform apply` would trigger an RDS instance
modification (brief restart).  The `ignore_changes = [password]` means
password rotation is handled out-of-band (AWS Secrets Manager rotation lambda
in production, manual `aws rds modify-db-instance` in demo).

## Module Dependency Graph

```
vpc ──────────────────────────────────────┐
 └──► rds                                 │
 └──► ec2 (demo) ──► iam ──► s3           │
 └──► ecs (mvp)  ──► iam ──► s3           │
 └──► alb (mvp)                           │
                                          │
sqs ──► iam ──────────────────────────────┤
                                          │
cloudfront ◄──────── ec2.public_ip (demo) │
           ◄──────── alb.dns_name  (mvp)  │
```

## Cost Breakdown

### Demo
| Service | Qty | Cost |
|---------|-----|------|
| EC2 t2.micro | 1 | Free (12 mo) → $8.5/mo |
| RDS db.t3.micro | 1 | Free (12 mo) → $13/mo |
| S3 | < 5 GB | Free (12 mo) → $0.12/mo |
| SQS | < 1M req | Free always |
| CloudFront | < 1TB | Free always |
| Route53 | 1 zone | $0.50/mo |
| **Total** | | **$0.50/mo (free tier)** |

### MVP
| Service | Qty | Cost |
|---------|-----|------|
| ECS Fargate | API×2+FE×1+Worker×1 | ~$60/mo |
| RDS db.t3.medium Multi-AZ | 1 | ~$50/mo |
| ElastiCache cache.t3.micro | 1 | ~$25/mo |
| ALB | 1 | ~$20/mo |
| NAT Gateway | 1 | ~$32/mo |
| S3 | < 50 GB | ~$1/mo |
| CloudFront | 1 dist | ~$2/mo |
| **Total** | | **~$190/mo** |
