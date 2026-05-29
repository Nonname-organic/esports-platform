# Phase 7 — Kubernetes (EKS + Helm + ArgoCD)

## Overview

Phase 7 targets the **Production** tier (~$1,100/month) where EKS replaces ECS Fargate.
The same container images from Phase 4 run unchanged; only the orchestration layer changes.

---

## Repository Layout

```
infrastructure/
  helm/
    esports-platform/
      Chart.yaml                 Helm chart metadata
      values.yaml                Default values (staging-safe)
      values-production.yaml     Production overrides
      templates/
        _helpers.tpl             Named template helpers
        serviceaccount.yaml      IRSA annotation
        configmap.yaml           Non-sensitive env vars
        externalsecret.yaml      Pulls secrets from AWS Secrets Manager
        api-deployment.yaml      API Deployment (rolling update, topology spread)
        api-service.yaml         ClusterIP Service
        api-hpa.yaml             HPA v2 (CPU + Memory metrics)
        frontend-deployment.yaml Frontend Deployment
        frontend-service.yaml
        frontend-hpa.yaml        HPA v2 (CPU metric)
        worker-deployment.yaml   Worker Deployment (no Service)
        worker-scaledobject.yaml KEDA ScaledObject + TriggerAuthentication
        ingress.yaml             AWS ALB Ingress Controller
        networkpolicy.yaml       Default-deny + allow rules
        poddisruptionbudget.yaml PDB for API and Frontend
  argocd/
    namespace.yaml               argocd + esports-platform namespaces
    appproject.yaml              Project RBAC (source repo + dest namespace)
    application.yaml             Application CRD (GitOps sync spec)
    notifications-config.yaml    Discord notifications on deploy events
  kubernetes/
    cluster-bootstrap.yaml       ResourceQuota, LimitRange, ClusterSecretStore
    irsa-policy.json             IAM policy attached to IRSA role
```

---

## Cluster Bootstrap Sequence

```bash
# 1. Create EKS cluster (Terraform Phase 6 extension or eksctl)
eksctl create cluster \
  --name esports-platform-production \
  --region ap-northeast-1 \
  --nodegroup-name standard \
  --node-type m5.large \
  --nodes-min 2 --nodes-max 6 \
  --managed

# 2. Install AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=esports-platform-production \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=<ALB_CONTROLLER_IRSA_ARN>

# 3. Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  -n external-secrets --create-namespace

# 4. Install KEDA
helm repo add kedacore https://kedacore.github.io/charts
helm install keda kedacore/keda -n keda --create-namespace

# 5. Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 6. Bootstrap cluster resources
kubectl apply -f infrastructure/kubernetes/cluster-bootstrap.yaml

# 7. Apply ArgoCD config
kubectl apply -f infrastructure/argocd/namespace.yaml
kubectl apply -f infrastructure/argocd/appproject.yaml
kubectl apply -f infrastructure/argocd/application.yaml
kubectl apply -f infrastructure/argocd/notifications-config.yaml

# ArgoCD will now sync the Helm chart automatically
```

---

## GitOps Deploy Flow

```
Developer pushes to main
        │
        ▼
GitHub Actions (Phase 8)
  ├─ docker build + push → GHCR
  └─ git commit: update image.tag in values-production.yaml
        │
        ▼
ArgoCD detects Git change (3-minute polling or webhook)
        │
        ▼
ArgoCD runs: helm template esports-platform ./helm/esports-platform \
               -f values.yaml -f values-production.yaml
        │
        ▼
Applies diff to EKS cluster
  ├─ Deployment rolling update (maxSurge=1, maxUnavailable=0)
  ├─ Old pods receive SIGTERM → preStop sleep(5) → terminationGracePeriod=30s
  └─ New pods pass readinessProbe before traffic routes to them
        │
        ▼
Discord notification: ✅ Deployment Succeeded / ❌ Deployment Failed
```

---

## IRSA (IAM Roles for Service Accounts)

In Phase 6 (EC2/ECS), the EC2 instance profile granted AWS permissions to all
processes on the host. In EKS, IRSA scopes permissions to individual pods via
a projected ServiceAccount token:

```
Pod → Kubernetes API (token) → AWS STS (AssumeRoleWithWebIdentity)
                                         ↓
                               IAM Role (IRSA policy)
                                         ↓
                               S3 / SQS / CloudWatch
```

The IRSA trust policy restricts which ServiceAccount can assume the role:
```json
{
  "Condition": {
    "StringEquals": {
      "oidc.eks.ap-northeast-1.amazonaws.com/id/XXXXXXXX:sub":
        "system:serviceaccount:esports-platform:esports-platform-sa"
    }
  }
}
```

No AWS access keys in environment variables. Credentials rotate automatically
every 12 hours via the projected token.

---

## Scaling Design

### API — HPA v2 (CPU + Memory)

| Metric | Target | Min | Max |
|--------|--------|-----|-----|
| CPU | 70% | 3 | 12 |
| Memory | 80% | 3 | 12 |

Scale-up: 2 pods per 60 s (tournament start spikes handled quickly).
Scale-down: 1 pod per 120 s, 5-minute stabilisation window (prevents flapping).

### Worker — KEDA SQS trigger

```
replicas = ceil(visible_messages / targetQueueLength)
         = ceil(50 / 10) = 5 replicas
```

Scales to **0** when queue is empty (save ~$3/day when no matches are running).
`minReplicaCount: 1` in production to avoid cold-start delay for the first match.

### Frontend — HPA v2 (CPU)

Lower traffic than API (SSG/ISR caches most pages). Target 60% CPU, 1–4 replicas.

---

## High Availability

| Mechanism | Protects Against |
|-----------|-----------------|
| `topologySpreadConstraints` (zone) | Single AZ failure |
| `PodDisruptionBudget` (minAvailable: 2) | Node drain during maintenance |
| `maxUnavailable: 0` rolling update | Zero-downtime deploys |
| `preStop` + `terminationGracePeriodSeconds` | In-flight request drops |
| ArgoCD `selfHeal: true` | Manual kubectl drift |
| ArgoCD `retry.limit: 3` | Transient sync failures |

---

## Security

| Layer | Mechanism |
|-------|-----------|
| AWS credentials | IRSA (no long-lived keys) |
| Application secrets | External Secrets Operator → AWS Secrets Manager |
| Inter-pod traffic | NetworkPolicy (default-deny + explicit allow) |
| Container root | `runAsNonRoot: true`, `runAsUser: 1000` |
| Filesystem | `readOnlyRootFilesystem: true` (API + Worker) |
| Linux capabilities | `drop: ["ALL"]` |
| Ingress TLS | ALB + ACM certificate |
| WAF (production) | AWS WAFv2 ACL via ALB annotation |

---

## Key Design Decisions

**Why Helm over plain YAML?**
Three services × three environments = 9 near-identical Deployment files if
written as raw YAML. Helm collapses this to one template with per-environment
`values-*.yaml` overlays. The `_helpers.tpl` functions (`esports-platform.image`,
`esports-platform.fullname`) ensure naming is consistent across every resource.

**Why ArgoCD over Flux?**
ArgoCD has a UI that makes the current sync state immediately visible — useful
for debugging and for demo purposes. Both support multi-source and Helm natively.
ArgoCD's `ignoreDifferences` cleanly handles the HPA/KEDA replica count drift
that would otherwise cause constant out-of-sync warnings.

**Why KEDA instead of a custom HPA metric?**
HPA scales on CPU/Memory. The worker's CPU usage is near-zero while long-polling
SQS (it's I/O-bound). KEDA's SQS trigger scales on `ApproximateNumberOfMessages`
which is the *actual* load signal. Scales to 0 between tournaments.

**Why External Secrets over Sealed Secrets?**
Sealed Secrets stores encrypted secrets in Git — viable, but rotating a secret
requires re-sealing and committing. External Secrets stores *references* to AWS
Secrets Manager in Git (no sensitive data) and pulls the values at sync time.
AWS Secrets Manager handles rotation, audit logs, and access control.

**`readOnlyRootFilesystem: true` exception for Frontend**
Next.js standalone server writes to `.next/cache` at runtime for ISR.
The cache volume is an `emptyDir` — ephemeral and per-pod, which is acceptable
since ISR fallback regeneration handles cache misses.
