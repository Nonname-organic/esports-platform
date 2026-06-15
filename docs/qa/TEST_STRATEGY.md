# Test Strategy — eSports Operating System

目的: 回帰テスト自動化 / CI-CD品質保証 / 本番事故防止 / 仕様書代替。
原則: **最少データで最大カバレッジ**。Golden Dataset 1本を全層（API/E2E/Visual）で再利用。

---

## 1. テストピラミッド & 配置
```
            E2E (Playwright)         ~10%  critical journeys / visual
        Integration + API (pytest)   ~30%  router×ケース, contract
      Unit (pytest / jest)           ~60%  rbac, services, components, hooks
       + Load(k6) / Security / Chaos  横断
```
| 層 | ツール | 置き場 |
|----|--------|--------|
| Backend unit/integration/api | pytest + httpx(ASGITransport) | `backend/tests/` |
| Frontend unit/component | jest + @testing-library | `frontend/src/**/__tests__` |
| E2E / Visual | Playwright | `frontend/tests/e2e/`, `frontend/playwright.config.ts` |
| Load | k6 | `k6/` |
| Security | pytest(`test_security.py`) + 手順 | `backend/tests/api/` |
| Contract | OpenAPIスキーマ検証 | `backend/tests/api/test_contract.py` |

---

## 2. Test Data Strategy（最少・再利用）
構成:
```
backend/tests/
  factories.py     # factory-boy: User/Team/Player/Tournament/Match ビルダー（属性既定＋override）
  conftest.py      # db/client/各ロールtoken/auth_headers fixtures（既存を拡張）
  seed/
    golden_seed.sql      # 決定論的・全状態を1ファイルで（CI/ローカル共通）
    golden_seed.py       # ORM版（型安全・冪等）
  fixtures/        # JSONレスポンス期待値（contract用）
  scenario/        # 複合シナリオ（E2E前提作成）
```
原則:
- **決定論的ID**（固定UUID）でテスト間参照を安定化。
- factory は「最小必須 + override」。1ペルソナ/1状態あたり1レコードを基本に、状態網羅を優先。
- 全画面で再利用: 同じGolden DBに対し API/E2E/Visual を実行。

対象エンティティ: users, teams, players, tournaments, matches, notifications, careers, scout, discord, riot。

---

## 3. Golden Dataset 仕様（`seed/golden_seed.sql` / `.py`）
固定パスワード: `Passw0rd!`（全テストユーザー共通）。

| 種別 | 値 |
|------|----|
| **Users/Roles** | admin@golden.test(admin), organizer@golden.test(organizer), captain@golden.test(player+captain), player@golden.test(player), guest=未ログイン |
| **大会** | 下書き / 受付中 / 開催中 / 完了 / キャンセル（日付はワーカー自動更新と整合） |
| **試合** | 未開始 / 進行中 / 完了 / 棄権(forfeit) / 異議申立(dispute) |
| **Career** | 高レート / 低レート / 新人(実績0) / 引退(is_active補助) |
| **Scout** | 募集中post / 応募済application / 推薦対象 |
| **通知** | 未読 / 既読 / 削除済(論理) |
| **Discord** | 接続済(DiscordLink有) / 未接続 |
| **Riot** | 同期済(synced_at有) / 未同期(puuid null) |

各レコードは決定論UUID（例 `00000000-0000-0000-0000-0000000000a1`=admin）で `golden.test` ドメイン。CIは投入→テスト→ロールバック(drop)で隔離。

---

## 4. API Test（pytest + httpx）
`backend/tests/api/` に router 単位。各テストで観点を網羅:
- **正常**: 期待ステータス/スキーマ。
- **異常**: 404/422/業務エラー。
- **境界**: limit/長さ/日時空。
- **認可**: token無=401 / 越権=403。
- **競合(race)**: 結果二重確定（分散ロック）→1成功/1 409。
- **タイムアウト**: 外部(Riot)モック遅延→graceful。

実行: `cd backend && pytest -q --cov=app --cov-report=term-missing`。
DB: `esports_test`（conftestが create_all/drop_all）。Redisはfake（conftest）。

---

## 5. E2E（Playwright）
`frontend/tests/e2e/`。Golden DBに対し実ブラウザで主要ジャーニー（E2E-001）。
- storageState でロール別ログインを使い回し（高速化）。
- data-testid 付与方針（主要操作要素）。
- Visual はE2Eと同セッションで撮影。

---

## 6. Load（k6）SLO
段階: VU 100 / 500 / 1000 / 5000（stages）。対象: Tournament一覧・Match取得・Analytics・Notification・(Discord publish)。

| 指標 | SLO |
|------|-----|
| http_req_duration p95 | < 500ms（読み取り）/ < 800ms（集計Analytics） |
| http_req_failed (error率) | < 1% |
| 一覧スループット | ≥ 300 req/s @1000VU |
| CPU (api) | < 80% sustained |
| Memory (api) | < 280MB（t3.micro 300M制限内） |

k6 thresholds で自動判定（超過=失敗）。

---

## 7. Security（OWASP ASVS マッピング）
| ASVS領域 | 対策/テスト |
|----------|-------------|
| V2 認証 | 弱PW拒否(AUTH-002)、brute耐性(SEC-006)、PW変更で現PW確認 |
| V3 セッション/JWT | exp/type/署名検証(SEC-005)、refresh≠access |
| V4 アクセス制御 | RBAC(SEC-002)、IDOR(SEC-004)、Bot権威RBAC(BOT-004) |
| V5 入力検証 | Pydantic、SQLi(ORMパラメタ化, SEC-003)、XSS(保存系エスケープ) |
| V10 SSRF/外部 | Riot/Discord URL検証(SEC-007)、Webhook |
| V11 ビジネスロジック | status遷移制約、二重確定ロック |
| API鍵 | `X-Bot-Secret` 必須(BOT-001/002)、RIOT_API_KEY漏洩防止 |
| Rate limit | login/Riot API（Redisカウンタ） |

`tests/api/test_security.py` に自動化（401/403/SQLi/JWT）。SSRF/XSSは手順＋一部自動。

---

## 8. Visual Regression（24画面 × 3端末）
`playwright/visual.spec.ts`。Desktop(1440) / Tablet(768) / Mobile(390)。
全Public/Auth画面で `toHaveScreenshot()`。差分閾値 `maxDiffPixelRatio: 0.02`。初回はベースライン生成（`--update-snapshots`）。

---

## 9. Chaos Engineering（対象 / 期待動作）
| 障害 | 注入 | 期待動作 |
|------|------|----------|
| Redis停止 | `docker stop app-redis-1` | キャッシュmiss→DBフォールバック、致命的500なし。通知/veto/Pub/Subは劣化許容 |
| DB停止 | `docker stop app-db`(RDS到達不可) | 5xx返却だがプロセス生存、復帰後自動回復(pool_pre_ping) |
| WS切断 | クライアント切断 | 再接続、欠落配信は再取得で整合 |
| SQS/Redisキュー停止 | キュー到達不可 | publishはnon-critical(try/except)、本処理継続 |
| Discord障害 | Bot/Gateway断 | api側は影響なし、イベントは滞留/再消費 |
| Riot障害/レート超過 | 429/5xx/遅延 | sync graceful degrade、APIキー無で連携のみ |

手順は `docker stop/start` + 影響API応答確認。期待を満たさない=本番事故リスクとして起票。

---

## 10. Coverage 目標 & Quality Gate
| 対象 | 最低 |
|------|------|
| Backend | 90% (`pytest --cov=app`) |
| Frontend | 85% (`jest --coverage`) |
| E2E | 主要ジャーニー80% |
| Critical Path | 100%（AUTH/TOUR lifecycle/MATCH result/BOT auth/RBAC） |

**PR拒否条件（Quality Gate）**:
1. Coverage が閾値未満。
2. P0テスト失敗（unit/integration/api/e2e）。
3. Contract破壊（OpenAPI差分でクライアント互換喪失）。
4. Visual diff（許容超過）未承認。
5. Security テスト失敗（401/403/SQLi/JWT）。
6. Load SLO 逸脱（nightly、p95/error）。

---

## 11. Mutation / Property-based / Snapshot / Contract
- **Mutation**: `mutmut`（backend、代表モジュール: services/match, rbac）。survival高=テスト不足の指標。
- **Property-based**: `hypothesis`（入力検証/境界、例: register email/password、score計算）。
- **Snapshot**: jest（コンポーネント）+ Playwright（画面）。
- **Contract**: `/openapi.json` をスナップショット化し差分検知（破壊的変更を検出）。

---

## 12. CI/CD（`.github/workflows/qa.yml`）
ジョブ（並列＋依存）:
```
lint  ──┐
unit ───┼─ integration ─ api ─ coverage(gate) ─ report
        ├─ e2e (playwright, golden seed) ─ visual
        └─ security
nightly: load(k6) / mutation / chaos(手動trigger)
```
- PR: lint/unit/integration/api/e2e/security/coverage を必須。
- main merge後: visual baseline更新, nightly load。
- 成果物: coverage(html/lcov), playwright report, k6 summary を artifacts へ。

---

## 13. ローカル実行 早見
```bash
# Backend
cd backend && pytest -q --cov=app --cov-report=term-missing
# Golden seed（test DB）
psql "$TEST_DB_URL" -f tests/seed/golden_seed.sql   # or python -m tests.seed.golden_seed
# Frontend unit
cd frontend && npm test
# E2E + Visual
cd frontend && npx playwright test
# Load
k6 run k6/tournament.js
```
