# Test Case Catalog — eSports Operating System

> ID命名: `<AREA>-NNN`。Automation: ✅自動化済 / 🟡自動化対象(scaffold) / 👤手動。Priority: P0/P1/P2。
> Precondition は Golden Dataset（[TEST_STRATEGY.md §Golden](./TEST_STRATEGY.md)）のペルソナ/状態を参照。

## AUTH — 認証
| ID | Title | Precondition | Steps | Expected | Pri | Auto |
|----|-------|--------------|-------|----------|-----|------|
| AUTH-001 | 新規登録 正常 | 未登録email | POST /auth/register {email,username,password} | 201, UserResponse, hashed_password非含 | P0 | ✅ |
| AUTH-002 | 弱パスワード拒否 | – | password=英小文字のみ | 422 | P0 | ✅ |
| AUTH-003 | email重複拒否 | 既存email | 同emailで登録 | 4xx(重複) | P0 | ✅ |
| AUTH-004 | ログイン 正常 | 登録済 | POST /auth/login | 200, access+refresh, role claim | P0 | ✅ |
| AUTH-005 | ログイン 誤PW | 登録済 | 誤password | 401 | P0 | ✅ |
| AUTH-006 | refresh 正常 | 有効refresh | POST /auth/refresh | 200 新token | P0 | ✅ |
| AUTH-007 | refresh 無効 | 改ざんtoken | – | 401 | P1 | ✅ |
| AUTH-008 | /me 認証必須 | token無し | GET /auth/me | 401 | P0 | ✅ |
| AUTH-009 | パスワード変更(現PW確認) | player | PATCH /auth/password | 204、新PWでlogin可 | P1 | ✅ |
| AUTH-010 | パスワード変更 現PW誤 | player | 誤current_password | 401 | P1 | ✅ |
| AUTH-011 | メール変更(PW確認/重複検査) | player | PATCH /auth/email | 200/409重複 | P1 | ✅ |
| AUTH-012 | 退会(論理無効化) | player | DELETE /auth/account | 204、以後login不可 | P1 | ✅ |
| AUTH-013 | access tokenでrefresh不可 | access token | refreshにaccess | 401(type検証) | P1 | 🟡 |

## TOUR — 大会
| ID | Title | Precondition | Steps | Expected | Pri | Auto |
|----|-------|--------------|-------|----------|-----|------|
| TOUR-001 | 一覧 公開取得 | seed | GET /tournaments | 200, is_public のみ | P0 | ✅ |
| TOUR-002 | 月フィルタ | seed各月 | ?month=YYYY-MM | 該当月に重なる大会のみ | P1 | ✅ |
| TOUR-003 | game/statusフィルタ | seed | ?game=&status= | 絞込一致 | P1 | ✅ |
| TOUR-004 | cursorページング | 13+件 | limit=12→cursor | 重複なし/has_next正 | P1 | 🟡 |
| TOUR-005 | 作成 organizer権限 | organizer | POST /tournaments | 201 | P0 | ✅ |
| TOUR-006 | 作成 player拒否 | player | POST /tournaments | 403 | P0 | ✅ |
| TOUR-007 | 詳細取得 | seed | GET /tournaments/{id} | 200 detail(rules/dates) | P0 | ✅ |
| TOUR-008 | 詳細404 | – | 不在id | 404 | P1 | ✅ |
| TOUR-009 | status遷移 owner | organizer所有 | PATCH /status draft→registration_open | 200 | P0 | ✅ |
| TOUR-010 | status遷移 非owner拒否 | 別organizer | PATCH /status | 403 | P0 | ✅ |
| TOUR-011 | 無効status遷移拒否 | completed | →ongoing | 4xx(BusinessRule) | P1 | 🟡 |
| TOUR-012 | 登録/承認フロー | open大会+team | register→PATCH registration approve | 204/200 | P0 | ✅ |
| TOUR-013 | 登録一覧 organizer専用 | player | GET /registrations | 403 | P1 | ✅ |
| TOUR-014 | Webチェックイン(自team) | approved登録player | POST /check-in | 200 checked_in_at | P1 | ✅ |
| TOUR-015 | 自動status(worker) | dates整合 | ワーカー実行 | 受付→開催中→終了へ自動遷移 | P0 | 👤/🟡 |

## BRKT — ブラケット
| ID | Title | Precondition | Steps | Expected | Pri | Auto |
|----|-------|--------------|-------|----------|-----|------|
| BRKT-001 | 生成 | 承認チーム複数 | POST /tournaments/{id}/bracket | 201 rounds構造 | P0 | ✅ |
| BRKT-002 | 取得 | 生成済 | GET /bracket | 200 rounds/matches | P0 | ✅ |
| BRKT-003 | 未生成取得 | 未生成 | GET /bracket | 404/空 | P1 | 🟡 |
| BRKT-004 | 勝者→次戦自動配置 | bracket+result | 結果確定 | next_matchにwinner | P0 | 🟡 |

## MATCH — 試合
| ID | Title | Precondition | Steps | Expected | Pri | Auto |
|----|-------|--------------|-------|----------|-----|------|
| MATCH-001 | 取得 | seed match | GET /matches/{id} | 200 detail(games/banpicks) | P0 | ✅ |
| MATCH-002 | 開始 organizer | scheduled | PATCH /start | 204 ongoing+started_at | P0 | ✅ |
| MATCH-003 | 開始 二重不可 | ongoing | PATCH /start | 4xx | P1 | 🟡 |
| MATCH-004 | スコア更新 | ongoing | POST /games/{n}/score | 204 winner算出 | P1 | 🟡 |
| MATCH-005 | 結果確定 | ongoing | POST /result {winner_id} | 204 completed+winner | P0 | ✅ |
| MATCH-006 | 結果 不正winner拒否 | ongoing | 非参加team | 4xx | P0 | ✅ |
| MATCH-007 | 結果 二重確定防止(分散ロック) | ongoing | 同時POST result×2 | 1件成功/1件409 | P0 | 🟡(race) |
| MATCH-008 | Ban/Pick登録 | scheduled/ongoing | POST /banpick | 204 | P1 | 🟡 |
| MATCH-009 | 自動進行→Discordチャンネル | discord設定済 | 開始/確定 | create/archiveイベントpublish | P1 | 🟡 |

## PLYR — プレイヤー
| ID | Title | Precondition | Steps | Expected | Pri | Auto |
|----|-------|--------------|-------|----------|-----|------|
| PLYR-001 | 作成 | login | POST /players | 201 | P1 | ✅ |
| PLYR-002 | /me | player有 | GET /players/me | 200 player | P1 | ✅ |
| PLYR-003 | 詳細 | seed | GET /players/{id} | 200 | P1 | ✅ |
| PLYR-004 | stats(新規=0) | 新規player | GET /players/{id}/stats | 200 zero値、404不可 | P0 | ✅ |
| PLYR-005 | career/achievements/rating-history | seed | 各GET | 200 schema一致 | P1 | 🟡 |
| PLYR-006 | 一覧 game/regionフィルタ | seed | GET /players?game= | 一致 | P2 | 🟡 |

## TEAM — チーム
| ID | Title | Precondition | Steps | Expected | Pri | Auto |
|----|-------|--------------|-------|----------|-----|------|
| TEAM-001 | 作成(logo/banner presigned長URL) | login | POST /teams | 201、banner_url保存 | P0 | ✅ |
| TEAM-002 | 詳細/メンバー | seed team | GET /teams/{id}, /members | 200 | P1 | ✅ |
| TEAM-003 | メンバー追加 owner | owner | POST /members | 200/201 | P1 | ✅ |
| TEAM-004 | メンバー追加 非owner拒否 | 他user | POST /members | 403 | P1 | 🟡 |
| TEAM-005 | career/achievements/rivals | seed | 各GET | 200 | P2 | 🟡 |

## SCOUT — スカウト
| ID | Title | Precondition | Steps | Expected | Pri | Auto |
|----|-------|--------------|-------|----------|-----|------|
| SCOUT-001 | 選手検索(フィルタ) | seed players | GET /scout/players?role=&looking_only= | 200一致 | P1 | ✅ |
| SCOUT-002 | チーム検索 | seed teams | GET /scout/teams | 200 | P1 | ✅ |
| SCOUT-003 | 募集投稿 | login | POST /scout/recruitment | 200/201 | P1 | ✅ |
| SCOUT-004 | 応募(重複拒否) | post有 | POST /apply ×2 | 1成功/1 4xx | P1 | 🟡 |
| SCOUT-005 | 双方向レコメンド | seed | GET /recommendations/{teams,players}/{id} | 200 score/breakdown | P2 | 🟡 |

## CAR — Career
| ID | Title | Precondition | Steps | Expected | Pri | Auto |
|----|-------|--------------|-------|----------|-----|------|
| CAR-001 | player career集計 | match済player | GET /players/{id}/career | 200 win_rate/kda整合 | P1 | 🟡 |
| CAR-002 | team career/rivals | match済team | GET /teams/{id}/career,/rivals | 200 | P2 | 🟡 |
| CAR-003 | rating-history | rating有 | GET /rating-history | 200 時系列 | P2 | 🟡 |

## NOTIF — 通知
| ID | Title | Precondition | Steps | Expected | Pri | Auto |
|----|-------|--------------|-------|----------|-----|------|
| NOTIF-001 | 一覧(本人) | 通知有player | GET /notifications | 200 自分のみ | P1 | ✅ |
| NOTIF-002 | 他人の通知不可 | userA/userB | A tokenでB通知参照不可 | 0件/403 | P0 | ✅ |
| NOTIF-003 | 未読数 | 未読有 | GET /unread-count | 正 | P1 | ✅ |
| NOTIF-004 | 既読/全既読 | 未読有 | PATCH /read,/read-all | 204 未読減 | P1 | 🟡 |
| NOTIF-005 | 削除 | 通知有 | DELETE /{id} | 204 | P2 | 🟡 |

## ANLY — 分析
| ID | Title | Precondition | Steps | Expected | Pri | Auto |
|----|-------|--------------|-------|----------|-----|------|
| ANLY-001 | player stats | seed | GET /analytics/players/{id}/stats?game= | 200 | P1 | 🟡 |
| ANLY-002 | map stats | seed | GET /analytics/maps/stats?game= | 200 list | P1 | 🟡 |
| ANLY-003 | compositions | seed | GET /analytics/compositions?game= | 200 | P2 | 🟡 |
| ANLY-004 | tournament summary | seed | GET /analytics/tournaments/{id}/summary | 200 | P1 | 🟡 |

## ADMIN
| ID | Title | Precondition | Steps | Expected | Pri | Auto |
|----|-------|--------------|-------|----------|-----|------|
| ADMIN-001 | dashboard admin専用 | admin | GET /admin/dashboard | 200 | P0 | ✅ |
| ADMIN-002 | dashboard 非admin拒否 | player | GET /admin/dashboard | 403 | P0 | ✅ |

## DISC — Discord
| ID | Title | Precondition | Steps | Expected | Pri | Auto |
|----|-------|--------------|-------|----------|-----|------|
| DISC-001 | リンク状態 | login | GET /discord/link | 200 null/連携 | P1 | ✅ |
| DISC-002 | コード発行 | login | POST /discord/link-code | 200 6桁 | P1 | ✅ |
| DISC-003 | コード連携(bot) | code発行済 | POST /bot/link {code}+X-Discord-User-Id | 200 DiscordLink作成 | P0 | ✅ |
| DISC-004 | 連携解除 | 連携済 | DELETE /discord/link | 204 | P1 | ✅ |
| DISC-005 | setup organizer専用 | player | POST /discord/setup/{id} | 403 | P1 | 🟡 |

## BOT — Botサービス（/bot/*）
| ID | Title | Precondition | Steps | Expected | Pri | Auto |
|----|-------|--------------|-------|----------|-----|------|
| BOT-001 | secret必須 | – | /bot/resolve（secret無） | 401 | P0 | ✅ |
| BOT-002 | secret誤り拒否 | – | X-Bot-Secret=wrong | 401 | P0 | ✅ |
| BOT-003 | resolve(連携→role) | 連携済 | GET /bot/resolve | role/teams返却 | P0 | ✅ |
| BOT-004 | report 権威RBAC | playerのみ | POST /bot/matches/{id}/report | 403(captain/owner必須) | P0 | 🟡 |
| BOT-005 | check-in self | 登録済player | POST /bot/tournaments/{id}/check-in | 200 | P1 | 🟡 |
| BOT-006 | metrics/errors ingest | secret | POST /bot/metrics,/errors | 200 保存 | P2 | 🟡 |

## RIOT
| ID | Title | Precondition | Steps | Expected | Pri | Auto |
|----|-------|--------------|-------|----------|-----|------|
| RIOT-001 | profile取得 | – | GET /riot/profile/{id} | 200 null可 | P2 | 🟡 |
| RIOT-002 | link(キー無→graceful) | RIOT_API_KEY無 | POST /riot/link | 連携作成(puuid null) | P2 | 🟡 |
| RIOT-003 | sync(キー無拒否) | キー無 | POST /riot/sync/{id} | 4xx 明示 | P2 | 🟡 |

## SEC — セキュリティ（OWASP ASVS）
| ID | Title | Steps | Expected | Pri | Auto |
|----|-------|-------|----------|-----|------|
| SEC-001 | 認証必須エンドポイント | token無で各保護API | 401 | P0 | ✅ |
| SEC-002 | RBAC越権 | player→organizer/admin操作 | 403 | P0 | ✅ |
| SEC-003 | SQLi | `' OR 1=1--` をクエリ/body | 安全(ORMパラメタ化)・漏洩なし | P0 | ✅ |
| SEC-004 | IDOR | 他人リソースID操作 | 403/404 | P0 | 🟡 |
| SEC-005 | JWT改ざん/期限 | alg none/exp切れ | 401 | P0 | ✅ |
| SEC-006 | Rate limit(brute) | login連打 | 制限/遅延 | P1 | 🟡 |
| SEC-007 | Webhook/SSRF(Riot/Discord) | 内部URL混入 | ブロック | P1 | 📋 |
| SEC-008 | XSS(保存系) | <script>名 | エスケープ表示 | P1 | 👤/🟡 |
| SEC-009 | Bot secret漏洩耐性 | /bot/* secret必須 | 401 | P0 | ✅ |

## E2E — ジャーニー（Playwright）
| ID | Title | Flow | Pri | Auto |
|----|-------|------|-----|------|
| E2E-001 | 主要導線 | 登録→チーム作成→大会参加→チェックイン→試合進行→結果報告→Career更新→Scout更新→通知確認 | P0 | ✅ |
| E2E-002 | organizer大会運営 | 作成→公開→承認→ブラケット→結果確定 | P0 | 🟡 |
| E2E-003 | 未ログイン導線 | 保護画面→ログイン案内→ログイン後復帰 | P1 | 🟡 |
| E2E-004 | サイドバー最小化/永続 | 折りたたみ→reload維持 | P2 | 🟡 |

## VIS — ビジュアルリグレッション（24画面 × Desktop/Tablet/Mobile）
| ID | 対象 | Pri | Auto |
|----|------|-----|------|
| VIS-001..024 | 全Public/Auth画面のスクショ比較 | P1 | ✅(playwright/visual.spec.ts) |
