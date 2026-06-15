# k6 負荷試験

eSports Platform の読み取り経路に対する段階的負荷試験。SLO を `thresholds` で自動判定（超過=失敗）。

## 前提
- [k6](https://k6.io/docs/get-started/installation/) インストール済み。
- 対象環境に **Golden Dataset** 投入済み（`backend/tests/seed/golden_seed.py`）。決定論UUIDで詳細/集計を叩く。

## 実行
```bash
# BASE_URL は API オリジン（nginx/CloudFront 経由の同一オリジンでも可）
k6 run -e BASE_URL=https://your-host -e PROFILE=load   tournament.js
k6 run -e BASE_URL=https://your-host -e PROFILE=stress match.js
k6 run -e BASE_URL=https://your-host -e PROFILE=spike  notification.js
```

## プロファイル（VU段階）
| PROFILE | 段階 | 用途 |
|---------|------|------|
| `smoke`  | 1 VU / 30s | 疎通・閾値確認（CI PR） |
| `load`   | →100 VU | 通常負荷 |
| `stress` | 100→500→1000 VU | 限界探索 |
| `spike`  | →5000 VU | スパイク耐性 |

## SLO（thresholds）
| 指標 | 閾値 |
|------|------|
| `http_req_duration` p95 | < 500ms（読み取り） / < 800ms（analytics 集計） |
| `http_req_failed` | < 1% |
| `http_reqs` rate | ≥ 300 req/s（tournament.js @負荷時のスループット目標） |

## スクリプト
| ファイル | 対象 |
|----------|------|
| `tournament.js` | 大会一覧 / 詳細 / ブラケット / ランキング |
| `match.js` | 試合詳細 / マップ集計 / プレイヤー集計（analytics） |
| `notification.js` | 認証(setup) → 通知一覧 / 未読数 / スカウト探索 |
| `lib/config.js` | BASE_URL・Golden ID・プロファイル・SLO・認証ヘルパー（共有） |

## CI
`.github/workflows/qa.yml` の `load` ジョブ（nightly / 手動）で `smoke` を実行し SLO を検証。
本格的な stress/spike はステージング環境に対して手動トリガー。
