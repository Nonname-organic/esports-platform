# Test Matrix — eSports Operating System

> Feature × Test Type. 各セルは「実装場所 / 主要ケース数」。Priority: P0=Critical Path（本番事故直結） / P1=主要 / P2=補助。
> Owner: BE=Backend, FE=Frontend, QA=SDET, SRE=Infra。
> 凡例: ✅実装あり / 🟡基盤＋代表実装（拡張は機械的） / 📋設計のみ(catalog参照)

## 全体カバレッジ目標
| 層 | 目標 | 計測 | Gate |
|----|------|------|------|
| Backend (unit+integration+api) | 90% | pytest-cov | PR blocking |
| Frontend (unit/component) | 85% | jest --coverage | PR blocking |
| E2E (critical journeys) | 80% | Playwright | PR blocking |
| Critical Path | 100% | E2E+API | PR blocking |

---

## Public 画面
| Feature | Unit | Integration | API | E2E | Load | Security | A11y/Visual | Priority | Owner |
|---------|------|-------------|-----|-----|------|----------|-------------|----------|-------|
| Landing | 🟡 | – | – | ✅ | 📋 | 📋 | ✅ | P2 | FE |
| Login | ✅ | ✅ | ✅(AUTH) | ✅ | 📋 | ✅(JWT/brute) | ✅ | P0 | BE/FE |
| Register | ✅ | ✅ | ✅(AUTH) | ✅ | 📋 | ✅(検証) | ✅ | P0 | BE/FE |
| Tournament List | 🟡 | ✅ | ✅(TOUR) | ✅ | ✅(k6) | 📋 | ✅ | P0 | FE/BE |
| Tournament Detail | 🟡 | ✅ | ✅(TOUR) | ✅ | ✅ | 📋 | ✅ | P0 | FE/BE |
| Bracket | 🟡 | ✅ | ✅(BRKT) | ✅ | 📋 | 📋 | ✅ | P1 | BE/FE |
| Match Center | 🟡 | ✅ | ✅(MATCH) | ✅ | ✅ | 📋 | ✅ | P0 | BE/FE |
| Player Detail | 🟡 | ✅ | ✅(PLYR/CAR) | ✅ | 📋 | 📋 | ✅ | P1 | FE/BE |
| Team Detail | 🟡 | ✅ | ✅(TEAM/CAR) | ✅ | 📋 | 📋 | ✅ | P1 | FE/BE |
| Scout | 🟡 | ✅ | ✅(SCOUT) | ✅ | 📋 | 📋 | ✅ | P1 | BE/FE |

## Auth 画面
| Feature | Unit | Integration | API | E2E | Load | Security | A11y/Visual | Priority | Owner |
|---------|------|-------------|-----|-----|------|----------|-------------|----------|-------|
| Dashboard | 🟡 | ✅ | ✅ | ✅ | 📋 | ✅(authz) | ✅ | P1 | FE |
| Notifications | 🟡 | ✅ | ✅(NOTIF) | ✅ | ✅ | ✅(他人不可) | ✅ | P1 | BE/FE |
| Analytics | 🟡 | ✅ | ✅(ANLY) | ✅ | ✅ | 📋 | ✅ | P1 | BE/FE |
| Tournament Create | ✅ | ✅ | ✅(TOUR) | ✅ | 📋 | ✅(organizer) | ✅ | P0 | FE/BE |
| Tournament Operation | ✅ | ✅ | ✅(TOUR/BRKT) | ✅ | 📋 | ✅(owner/RBAC) | ✅ | P0 | BE |
| Admin | 🟡 | ✅ | ✅(ADMIN) | ✅ | 📋 | ✅(admin only) | ✅ | P0 | BE |
| Player Create | ✅ | ✅ | ✅(PLYR) | ✅ | 📋 | ✅(本人) | ✅ | P1 | FE/BE |
| Team Create | ✅ | ✅ | ✅(TEAM) | ✅ | 📋 | ✅(owner) | ✅ | P1 | FE/BE |
| Recruitment | 🟡 | ✅ | ✅(SCOUT) | ✅ | 📋 | ✅(本人) | ✅ | P2 | BE/FE |
| User Settings | ✅ | ✅ | ✅(AUTH) | ✅ | – | ✅(pw確認) | ✅ | P1 | BE/FE |
| Discord Link | 🟡 | ✅ | ✅(DISC) | ✅ | – | ✅(secret) | ✅ | P1 | BE/FE |

## API（ルータ単位）
| Router | Unit | Integration | API(normal/abnormal/boundary/authz/race/timeout) | Contract | Load | Security | Priority | Owner |
|--------|------|-------------|---------------------------------------------------|----------|------|----------|----------|-------|
| Auth | ✅ | ✅ | ✅ | 🟡(OpenAPI) | 📋 | ✅ | P0 | BE |
| Tournament | ✅ | ✅ | ✅ | 🟡 | ✅ | ✅ | P0 | BE |
| Match | 🟡 | ✅ | ✅(race=分散ロック) | 🟡 | ✅ | ✅ | P0 | BE |
| Bracket | 🟡 | ✅ | ✅ | 🟡 | 📋 | ✅ | P1 | BE |
| Player | 🟡 | ✅ | ✅ | 🟡 | 📋 | ✅ | P1 | BE |
| Team | 🟡 | ✅ | ✅ | 🟡 | 📋 | ✅ | P1 | BE |
| Scout | 🟡 | ✅ | ✅ | 🟡 | 📋 | ✅ | P1 | BE |
| Career | 🟡 | ✅ | ✅ | 🟡 | 📋 | 📋 | P2 | BE |
| Notification | 🟡 | ✅ | ✅ | 🟡 | ✅ | ✅ | P1 | BE |
| Analytics | 🟡 | ✅ | ✅ | 🟡 | ✅ | 📋 | P1 | BE |
| Discord | 🟡 | ✅ | ✅ | 🟡 | 📋 | ✅(secret/oauth) | P1 | BE |
| Riot | 🟡 | ✅ | ✅ | 🟡 | 📋 | ✅(key/SSRF) | P2 | BE |
| Bot (/bot) | 🟡 | ✅ | ✅(X-Bot-Secret/on-behalf) | 🟡 | 📋 | ✅(RBAC権威) | P0 | BE |

## Discord Bot（15カテゴリ/93コマンド）
| Category | Unit(rbac/parse) | Integration(api_client) | Contract(/bot) | E2E(手動) | Security(RBAC) | Priority | Owner |
|----------|------------------|--------------------------|----------------|-----------|----------------|----------|-------|
| Account(link/whoami/unlink) | 🟡 | ✅ | ✅ | 📋 | ✅ | P0 | BE |
| Veto | 🟡 | ✅ | ✅ | 📋 | ✅(captain) | P1 | BE |
| Dice | ✅ | – | – | 📋 | – | P2 | BE |
| Match(report/confirm/dispute) | 🟡 | ✅ | ✅ | 📋 | ✅(captain/owner) | P0 | BE |
| Help | ✅ | – | – | 📋 | ✅(role表示) | P2 | BE |
| RBAC core | ✅ | – | – | – | ✅ | P0 | BE |

## 横断（Infra/品質）
| 観点 | 実装 | 場所 | Priority | Owner |
|------|------|------|----------|-------|
| Load (100/500/1000/5000) | ✅ | k6/ | P0 | SRE |
| Chaos (Redis/DB/WS/SQS/Discord/Riot) | 🟡(手順+期待) | docs/qa/TEST_STRATEGY.md §Chaos | P1 | SRE |
| Security (OWASP ASVS) | ✅ | tests/api/test_security.py + §Security | P0 | QA |
| Visual Regression (24画面×3端末) | ✅ | playwright/visual.spec.ts | P1 | FE |
| Mutation (代表) | 🟡(mutmut設定) | docs/qa §Mutation | P2 | QA |
| Property-based | 🟡(hypothesis代表) | tests/api/test_security.py他 | P2 | QA |
| Snapshot | ✅ | jest + playwright | P2 | FE |
| Contract | 🟡(OpenAPIスキーマ検証) | tests/api/test_contract.py | P1 | BE |
