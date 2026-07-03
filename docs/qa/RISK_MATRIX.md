# §14 Risk-Based Testing — Risk Matrix

全機能に Risk Score を付与し、テスト密度とゲート強度を配分する。
機械可読版: [risk_registry.json](risk_registry.json)（CI が読み取りゲートに使用可能）。

## スコア式
```
Risk = BusinessImpact × FailureProbability × UsageFrequency   (各 1〜5, 最大125)
```

## ティア分類
| Tier | Risk目安 | テスト要件 | ゲート |
|------|---------|-----------|--------|
| **P0** | ≥45 または重要保安 | **100% Unit / Integration / API / E2E** | いずれか失敗・Critical Path<100% で **PR Block** |
| **P1** | 20–44 | Unit + API 必須 / E2E は主要のみ | Coverage ≥85% |
| **P2** | <20 | smoke + visual | advisory |

## 登録（要約）
| 機能 | Tier | BI | FP | UF | Risk | 主テスト |
|------|------|----|----|----|------|----------|
| 認証 (login/register/JWT) | **P0** | 5 | 3 | 5 | **75** | AUTH-*, SEC-001/002/005 |
| 試合結果 報告/確定 | **P0** | 5 | 4 | 4 | **80** | MATCH-*, WRK-* |
| 大会作成 | **P0** | 5 | 3 | 4 | **60** | TOUR-* |
| 参加申請/承認 | **P0** | 5 | 3 | 4 | **60** | TOUR-register, E2E-001 |
| ブラケット生成/進行 | **P0** | 5 | 4 | 3 | **60** | BRKT-001/002/003 |
| Discord認証/連携 | **P0** | 4 | 4 | 3 | **48** | DISC-*, BOT-* |
| Riot同期 | **P0** | 4 | 4 | 3 | **48** | RIOT-*, FLAG-riot-* |
| 通知 | P1 | 3 | 3 | 4 | 36 | NOTIF-002, WRK-notification |
| Analytics集計 | P1 | 3 | 3 | 3 | 27 | ANLY-* |
| Career/戦績 | P1 | 3 | 3 | 3 | 27 | CAR-* |
| Scout探索/募集 | P1 | 3 | 3 | 3 | 27 | SCOUT-001/002 |
| 公開ページ | P2 | 2 | 2 | 4 | 16 | VIS-* |
| 管理補助 | P2 | 2 | 2 | 2 | 8 | ADMIN-* |

## P0 ルール（必達）
P0 の各機能は **Unit / Integration / API / E2E を 100%** で網羅。Critical Path カバレッジは [TEST_STRATEGY.md](TEST_STRATEGY.md) §10 の通り 100%。
未達は Quality Gate（[qa.yml](../../.github/workflows/qa.yml)）で PR をブロックする。

## 運用
- 新機能追加時は `risk_registry.json` に1行追加し Tier を決定（PRレビュー必須項目）。
- インシデント発生機能は FailureProbability を再評価し Tier を引き上げる（継続的品質監視）。
