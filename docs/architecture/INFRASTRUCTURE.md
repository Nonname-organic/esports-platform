# Infrastructure Architecture

## AWS Architecture Overview

```
Internet
    │
    ▼
CloudFront (CDN + WAF)
    │
    ├── S3 (Static Assets)
    │
    └── ALB (Application Load Balancer)
         │
         ├── ECS Fargate (Demo/MVP)
         │    ├── api (FastAPI)
         │    ├── worker (SQS Consumer)
         │    └── frontend (Next.js)
         │
         └── EKS (Production)
              ├── api-deployment (FastAPI x3)
              ├── worker-deployment (Worker x2)
              ├── frontend-deployment (Next.js x2)
              └── discord-bot (Bot x1)

## Event-Driven Flow

EventBridge
    │
    ├── Rule: TournamentCreated → SQS:tournament-queue → Worker:tournament-handler
    ├── Rule: MatchFinished → SQS:match-queue → Worker:match-handler
    ├── Rule: MatchFinished → SQS:analytics-queue → Worker:analytics-aggregator
    └── Rule: PlayerRegistered → SQS:notification-queue → Worker:notification-sender

## Database Architecture

RDS Aurora PostgreSQL (Multi-AZ)
    ├── Primary (Write)
    └── Read Replica (Analytics queries)

ElastiCache Redis
    ├── Session cache
    ├── Tournament bracket cache
    └── WebSocket pub/sub

## Monitoring

CloudWatch
    ├── API Latency (p50, p95, p99)
    ├── Error Rate
    └── WebSocket connections

Grafana
    ├── Tournament completion rate
    ├── Player engagement
    └── Match resolution time
```

## Kubernetes Manifest (Production)

```yaml
# EKS Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: esports-api
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: esports-api
  template:
    spec:
      containers:
      - name: api
        image: ghcr.io/org/esports-api:latest
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "2000m"
            memory: "2Gi"
        env:
        - name: ENVIRONMENT
          value: "prod"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: esports-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: esports-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```
