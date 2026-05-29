# Phase 8 — CI/CD (GitHub Actions)

## Overview

Phase 8 wires automated quality gates and multi-environment deployments onto the
platform built in Phases 1–7. Every push to `main` that touches application code
triggers a build → deploy pipeline; infrastructure changes go through a separate
Terraform workflow gated by a manual apply step.

---

## Workflow Map

```
┌─────────────────────────────────────────────────────────────────┐
│  Pull Request → main                                            │
│                                                                 │
│  pr-checks.yml                                                  │
│    ├── Backend: ruff + mypy                                     │
│    ├── Backend: pytest (postgres + redis service containers)    │
│    ├── Frontend: ESLint + tsc                                   │
│    └── Frontend: jest                                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Push to main (backend/ or frontend/ changed)                  │
│                                                                 │
│  build.yml                                                      │
│    └── Matrix: api | worker | frontend                         │
│         ├── docker buildx → GHCR (sha-<7>) + ECR (sha-<7>)    │
│         └── GHA layer cache (type=gha per service scope)       │
│                   │ workflow_run: completed                     │
│         ┌─────────┼──────────┐                                 │
│         ▼         ▼          ▼                                  │
│  deploy-demo  deploy-mvp  deploy-production                    │
│  (EC2 SSH)    (ECS)       (Helm values → ArgoCD)               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  infrastructure/terraform/** changed                            │
│                                                                 │
│  terraform.yml                                                  │
│    ├── PR: plan for changed environment(s), comment on PR      │
│    └── workflow_dispatch: apply (requires environment approval) │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  db-migrate.yml  (manual dispatch only)                        │
│    ├── demo: SSH → docker compose exec api alembic upgrade      │
│    ├── mvp:  ECS Exec → alembic upgrade                        │
│    └── prod: kubectl exec (API pod) → alembic upgrade          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Workflow Reference

| File | Trigger | Purpose |
|------|---------|---------|
| `pr-checks.yml` | PR → main | Quality gate (lint, types, tests) |
| `build.yml` | push to main (app paths) | Build + push to GHCR and ECR |
| `deploy-demo.yml` | workflow_run: Build & Push | SSH deploy to EC2 |
| `deploy-mvp.yml` | workflow_run: Build & Push | ECS rolling update |
| `deploy-production.yml` | workflow_run: Build & Push | Update Helm values → ArgoCD |
| `terraform.yml` | PR / manual dispatch | Plan on PR, apply on dispatch |
| `db-migrate.yml` | manual dispatch | Alembic upgrade per environment |

---

## Image Tagging

All three images (api, worker, frontend) are tagged identically on every build:

```
sha-<first 7 chars of GITHUB_SHA>   e.g.  sha-a3f9c12
latest
```

The `sha-` prefix makes tags human-readable in deploy logs and ECS task history.
`latest` is used as the fallback reference in docker-compose.prod.yml.

Both GHCR and ECR receive the same tag in a single `docker buildx build` run
(no second push step — two `--tag` values pointing to different registries).

---

## AWS Authentication (OIDC)

No long-lived AWS keys are stored as GitHub secrets. Every workflow that touches
AWS uses OpenID Connect:

```yaml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::ACCOUNT:role/github-actions-<scope>
    aws-region: ap-northeast-1
```

IAM roles and their trust policies follow least-privilege scoping:

| Role | Permissions |
|------|-------------|
| `github-actions-build` | `ecr:GetAuthorizationToken`, `ecr:BatchCheckLayerAvailability`, `ecr:PutImage`, `ecr:InitiateLayerUpload`, `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload` |
| `github-actions-mvp-deploy` | `ecs:DescribeTaskDefinition`, `ecs:RegisterTaskDefinition`, `ecs:UpdateService`, `ecs:ListTasks`, `ecs:ExecuteCommand`, `iam:PassRole` (task role) |
| `github-actions-production-deploy` | `eks:DescribeCluster` (for kubeconfig), no pod permissions (RBAC handles that) |
| `github-actions-terraform-plan` | `s3:GetObject` (state bucket), read-only on all services |
| `github-actions-terraform-apply-*` | Full state bucket + service write permissions, scoped per environment |

All trust policies include:
```json
"Condition": {
  "StringEquals": {
    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
    "token.actions.githubusercontent.com:sub": "repo:your-org/esports-platform:ref:refs/heads/main"
  }
}
```

---

## GitHub Environments

Three GitHub Environments gate production-affecting deploys:

| Environment | Protection rules | Used by |
|-------------|-----------------|---------|
| `demo` | None (auto-deploy) | deploy-demo.yml |
| `mvp` | Required reviewers: none (auto), secrets scoped to MVP | deploy-mvp.yml, db-migrate.yml |
| `production` | Required reviewers: 1, deployment branch: main | deploy-production.yml, db-migrate.yml |

The `production` environment reviewer gate prevents accidental production deploys.
In practice, this gate sits at the ArgoCD sync step (the Helm values commit) — a
reviewer approves the GitHub deployment, then the commit lands on main, and ArgoCD
syncs within 3 minutes.

---

## Docker Layer Caching

Build times drop from ~4 min to ~45 s on cache hits:

```yaml
cache-from: type=gha,scope=${{ matrix.service }}
cache-to: type=gha,mode=max,scope=${{ matrix.service }}
```

Each service (api, worker, frontend) has its own cache scope so a frontend change
doesn't evict the backend cache. `mode=max` caches all intermediate layers, not
just the final image.

---

## Demo Deploy Detail (EC2)

The EC2 host runs Docker Compose. `docker-compose.yml` uses `build:` contexts for
local development; `docker-compose.prod.yml` overrides `build: null` and sets
`image:` references to GHCR. The CI deploy merges both files:

```
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

GHCR login on the EC2 host uses the `GITHUB_TOKEN` passed via `appleboy/ssh-action`
`envs:` — no PAT stored on the host.

Migration order:
1. Pull new images
2. Restart containers (`up -d --remove-orphans`)
3. Poll `/health` until ready (12 × 5 s = 60 s max)
4. `alembic upgrade head`

---

## MVP Deploy Detail (ECS)

Three ECS services (api, worker, frontend) deploy in parallel via matrix jobs.
After all three stabilise, a separate `run-migration` job execs into a running API
task via ECS Exec (`aws ecs execute-command`).

`wait-for-service-stability: true` means the deploy job blocks until ECS reports
all new tasks healthy and old tasks drained — no race condition with the migration
step.

---

## Production Deploy Detail (ArgoCD GitOps)

The production workflow does **not** kubectl apply anything directly. It only:
1. Checks out the built commit
2. Updates `  tag: sha-xxxxxxx` in `values-production.yaml` via `sed`
3. Commits `[skip ci]` and pushes to main

ArgoCD detects the diff within 3 minutes (polling) or immediately (webhook), runs
`helm template` with the updated values, and applies the diff as a rolling update.

The `[skip ci]` commit message prefix prevents `pr-checks.yml` from re-triggering
on the tag-bump commit.

Rollback: `git revert HEAD`, push → ArgoCD restores the previous image tag.

---

## Terraform Workflow Detail

**PR flow:**
1. Detect which environments changed from `git diff origin/main...HEAD`
2. If only shared module files changed, plan all three environments
3. `terraform plan -no-color` output posted as a sticky PR comment (updates on
   re-push rather than appending new comments)

**Apply flow:**
- `workflow_dispatch` only — never automated on merge
- Requires `environment` input (demo | mvp | production)
- `terraform apply -auto-approve` with environment-specific OIDC role
- Production apply role requires the `production` GitHub Environment approval

---

## Key Design Decisions

**Why `workflow_run` instead of a single pipeline?**
`workflow_run` lets deploy workflows trigger from the `Build & Push` completion
without being part of the same YAML. Each environment can be re-triggered
independently (`workflow_dispatch`) without re-running the build.

**Why push to both GHCR and ECR in one build?**
ECS Fargate can pull from ECR natively without credentials config in the task
definition. EKS (Phase 7) uses GHCR with imagePullSecrets. Building once and
tagging twice avoids a separate re-tagging or push step.

**Why `provenance: false` in the build action?**
Docker Buildx v0.11+ generates OCI attestation manifests by default, producing a
multi-arch index even for single-arch images. ECS task definitions that reference a
manifest list (instead of a direct image digest) can fail to pull. `provenance:
false` forces a single-arch image manifest.

**Why separate `db-migrate.yml` and not auto-run on every deploy?**
Auto-migration on every deploy creates a race: if two deployments run back-to-back,
the second migration runs before the first deploy is fully stable. Schema migrations
also need to be reviewed explicitly before applying to production. Manual dispatch
with a `confirm=yes` gate makes intent explicit.

**Why `cancel-in-progress: false` on deploy concurrency groups?**
Deploy jobs should queue, not cancel. If a second push lands while a deploy is in
progress, cancelling the first deploy mid-flight (between task registration and
service stabilisation) would leave the service in an inconsistent state.

---

## Required Secrets and Variables

### Repository Secrets

| Secret | Used by |
|--------|---------|
| `AWS_ACCOUNT_ID` | build, all deploy and terraform workflows |
| `DEMO_EC2_HOST` | deploy-demo, db-migrate |
| `DEMO_EC2_SSH_KEY` | deploy-demo, db-migrate |

### GitHub Environment Variables

| Scope | Variable | Value |
|-------|----------|-------|
| `demo` | `DEMO_DOMAIN` | e.g. `demo.esports-platform.example.com` |
| `production` | `PRODUCTION_DOMAIN` | e.g. `esports-platform.example.com` |

### OIDC IAM Roles to Create

```bash
# One role per trust boundary; created in Terraform or manually.
github-actions-build                       # ECR push
github-actions-mvp-deploy                  # ECS update + exec
github-actions-production-deploy           # EKS kubeconfig
github-actions-terraform-plan              # read-only state
github-actions-terraform-apply-demo        # full demo infra
github-actions-terraform-apply-mvp         # full mvp infra
github-actions-terraform-apply-production  # full production infra
```
