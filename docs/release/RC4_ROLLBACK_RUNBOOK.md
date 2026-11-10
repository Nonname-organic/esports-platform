# RC4 切り戻しの手順（ConoHa VPS）

- 作成: 2026-11-11（RC4 自律完遂の工程）。[RC2 の手順](RC2_ROLLBACK_RUNBOOK.md)を置き換える
- 方針: **イメージだけを、控えた digest で戻す。DB は戻さない**（`alembic downgrade` を使わない。理由は 4 章）
- 戻す先は、Deploy の workflow が入れ替えの前に控えたイメージ（RC4 の公開では `sha-c0a80ad`）

## 1. 前提

Deploy の workflow（[公開の手順](RC4_DEPLOYMENT_RUNBOOK.md)の 4-1）が、入れ替えの前に `~/rollback-images-sha-<新>.yml` を作る。
同じ版のデプロイをやり直しても上書きしないので、最初の入れ替えの前の版が残る。中身は 4 サービスのイメージの digest。

```yaml
services:
  api:
    image: ghcr.io/nonname-organic/esports-platform-api@sha256:<digest>
  worker:
    image: ghcr.io/nonname-organic/esports-platform-worker@sha256:<digest>
  scheduler:
    image: ghcr.io/nonname-organic/esports-platform-api@sha256:<digest>
  frontend:
    image: ghcr.io/nonname-organic/esports-platform-frontend@sha256:<digest>
```

digest が取れなかったサービスはタグのまま書かれる。そのときはタグで戻し、取得したイメージの digest を作業記録に残す。

## 2. 戻すかどうかの判断

| 状況 | 対応 |
|---|---|
| 4-2・4-3 で止まった（設定の検査・バックアップ） | 戻さない。旧コードのまま動いている |
| 4-4 で止まった（マイグレーション。開催中の大会がある・ロックが取れない） | 戻さない。版は 027 のまま、旧コードのまま動いている。大会が終わってから出し直す |
| 4-5 の後に readiness が通らない、5xx が続く | 戻す（3 章） |
| 4-6 の公開の確認が失敗した（旧コードの間に旧方式の大会の試合が始まった、旧方式の大会が開催中になった） | 戻す（3 章）。旧コードは旧方式の大会をそのまま進められる。大会が終わってから出し直す（6 章） |
| 特定の機能だけの不具合で、データを壊していない | 修正版を出すか、戻すかを判断する |

## 3. 手順

```bash
cd /opt/app
# 1. 同じ版の再デプロイを防ぐ
gh workflow disable deploy-demo.yml --repo Nonname-organic/esports-platform

# 2. 状態を控える
docker compose ps
docker compose exec -T postgres psql -U esports_user -d esports_db -tAc 'select version_num from alembic_version'   # 032
for q in match_events notification_events analytics_events discord_events; do
  printf '%s: ' "$q"; docker compose exec -T redis redis-cli LLEN "queue:$q"
done

# 3. 控えた digest を compose に重ねる（このシェルの中だけ）
NEWTAG=sha-<新>
export COMPOSE_FILE="$(grep '^COMPOSE_FILE=' .env | cut -d= -f2-):$HOME/rollback-images-$NEWTAG.yml"
export IMAGE_ORG=nonname-organic IMAGE_TAG=sha-c0a80ad      # ほかのイメージ参照を正しい形に保つため。実際の版は digest が決める
docker compose config --images                              # api・worker・frontend が控えた digest であることを目で確かめる

# 4. 取得して入れ替える
docker compose pull api worker scheduler frontend
docker compose up -d api worker scheduler frontend

# 5. 確かめる
curl -fsS https://app.axelia-esports.jp/health/ready
for svc in api worker scheduler frontend; do
  printf '%s: ' "$svc"; docker inspect --format '{{.Config.Image}}' "$(docker compose ps -q $svc)"
done
docker compose exec -T postgres psql -U esports_user -d esports_db -tAc 'select version_num from alembic_version'   # 032 のまま

ROLLBACK_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ); echo "$ROLLBACK_AT"   # 作業記録に残す（5 章・6 章で使う）
unset COMPOSE_FILE IMAGE_ORG IMAGE_TAG
```

- **旧イメージの中で `alembic` を実行しない。** 旧コードは 028 以降を知らないので失敗する。版は psql で見る
- `.env` に `COMPOSE_FILE` が無いときは、Deploy の workflow と同じ `docker-compose.yml:docker-compose.prod.yml`（または `vars.DEMO_COMPOSE_FILES` の値）を使う
- 2 のキューが空でなければ、処理が終わるのを待ってから 4 に進む
- nginx・postgres・redis は入れ替えない

完了の判定:

- [ ] 4 サービスが控えた digest、readiness が 200、`alembic_version` は 032 のまま
- [ ] ログイン・大会一覧・詳細・試合ページが開く。5xx が増えない

## 4. DB を戻さない理由と、旧コードで動かす間のデータ

旧コード（`sha-c0a80ad`）は 032 のスキーマで動く。028〜032 は表・列・制約・トリガーの追加とデータの補正だけで、旧コードが使う列を消したり、
型を変えたりしていない。追加の列はすべて NULL 可か既定値つき（`team_members.consent` は `unconfirmed`、`tournaments.roster_mode` は `roster`）。
旧コードの書き込みが RC4 の制約に当たるのは、同じチームに同じ選手の現役の所属を 2 行作ろうとしたときだけ（一意制約で 500。旧コードの画面は重複を作らない）。

確かめたこと（2026-11-11、使い捨ての DB。本番では未実施）: 旧コード（`c0a80ad`）のテスト 92 件を、RC4 のマイグレーション（001〜032）で作ったスキーマの上で
流し、PostgreSQL 15・16 の両方ですべて通った（旧コードのテストの準備だけを、RC4 のマイグレーションを使うように変えた）。
公開の手順の 4-4 から 4-5 の間と、切り戻した後の旧コードの動きの根拠にする。

`alembic downgrade` を使わない理由:
- 028〜030 は RC2 の手順のとおり戻さない（結果報告の表が消える・募集の投稿が連鎖して消える）
- 031・032 を戻すと、RC4 の間に作られた招待・名簿・出場登録・交代・異議・訂正の記録が消え、元に戻せない

旧コードで動かす間に書かれるデータと、RC4 に戻したときの扱い:

| 書き込み | RC4 に戻したとき | 対応 |
|---|---|---|
| メンバーの追加（旧コードは本人の承諾なしに足す） | `consent` は `unconfirmed`（本人未確認）。移行期間中は数え、本人が確認・否認する | なし（RC4 の規則どおり） |
| 大会の作成 | `roster_mode` は既定の `roster` になる。名簿が無い | 5 章 |
| 名簿の方式の大会の試合の開始・成績の保存・結果 | 出場登録が無い（旧コードは作らない）。RC4 では、出場登録の無い試合の成績は個人の帰属に数えない | 5 章 |
| 旧方式の大会 | 旧コードは今までどおり進める | 6 章（再公開の判定） |
| 招待・名簿・出場登録・交代・異議・訂正の記録 | 旧コードは読まない。残っているので、RC4 に戻すとそのまま使われる | なし |

## 5. 切り戻しの間の roster の大会（Q30）

切り戻しの間に旧コードが作成・開始した大会は `roster`（既定）で、名簿も出場登録も無い。RC4 に戻す前に一覧を出す。

```bash
docker compose exec -T postgres psql -U esports_user -d esports_db -v since="$ROLLBACK_AT" <<'SQL'
SELECT id, status, created_at
  FROM tournaments
 WHERE roster_mode = 'roster' AND (created_at >= :'since' OR updated_at >= :'since')
 ORDER BY created_at;
SQL
```

- 開催中のものがあれば、RC4 の再公開を延期する（名簿の無い開催中の大会は、RC4 では試合の開始・成績の保存ができない）
- 未開始のものは、RC4 に戻した後に各チームが名簿を作れば、そのまま進められる
- 完了したものは、そのままだと個人の帰属が付かない（出場登録が無いため）。旧方式（所属の期間で帰属）に戻すときは、
  **1 回だけの作業**として、トリガーを止めた 1 つのトランザクションの中で、理由を記録して戻す。アプリには `legacy` に戻す機能を作らない

```bash
# 対象の大会の ID を確かめてから、IDS にカンマ区切りの引用付きで入れる（例: 'uuid1','uuid2'）
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U esports_user -d esports_db -v reason='切り戻しの間に旧コードで完了した大会' <<'SQL'
BEGIN;
ALTER TABLE tournaments DISABLE TRIGGER trg_tournaments_roster_mode_guard;
INSERT INTO admin_corrections (id, kind, tournament_id, reason, before, after)
SELECT gen_random_uuid(), 'roster_mode_change', t.id, :'reason',
       jsonb_build_object('roster_mode', t.roster_mode), jsonb_build_object('roster_mode', 'legacy')
  FROM tournaments t
 WHERE t.id IN (IDS) AND t.roster_mode = 'roster' AND t.status = 'completed';
UPDATE tournaments SET roster_mode = 'legacy'
 WHERE id IN (IDS) AND roster_mode = 'roster' AND status = 'completed';
ALTER TABLE tournaments ENABLE TRIGGER trg_tournaments_roster_mode_guard;
COMMIT;
SQL
```

- `ALTER TABLE ... DISABLE TRIGGER` は表のロックを取り、トランザクションの中だけで効く。失敗すれば全体が戻り、トリガーも有効のまま
- 同じ SQL をテスト（`backend/tests/test_rc4_migrations.py`）で確かめた（戻した大会が `legacy`、訂正の記録が 1 行、作業の後もトリガーが効く）
- 本番での実行は承認を得てから行う

## 6. RC4 を出し直す

- [公開の手順](RC4_DEPLOYMENT_RUNBOOK.md)の 1 からやり直す。マイグレーションは 032 まで済んでいるので何もしない。公開の確認（4-6）は同じ条件で行う
- 開催中の大会（旧方式・5 章の roster のどちらも）があれば延期する

## 7. データだけを戻す（バックアップからの復元）

[公開の手順](RC4_DEPLOYMENT_RUNBOOK.md)の 4-3 のバックアップは、公開の直前（版 027）の DB。復元すると、公開の後のすべての書き込みが消える。

- 復元は最後の手段で、承認が要る。`scripts/restore-db.sh <ファイル>`（確認の入力を求める）
- **復元した DB は版 027。旧コード（`sha-c0a80ad`）でだけ動く。** RC4 のイメージで動かすと、起動はするが 028 以降の表・列が無く、多くの API が 500 になる。
  RC4 を出し直すときは、もう一度 Deploy（マイグレーションを含む）を通す
- 復元した後は、公開の後に登録・変更した利用者・チーム・大会の情報が失われたことを、影響を受けた利用者に伝える必要がある（範囲は復元の前の DB との比較でしか分からない）
- RC4 の公開の後に取った定期のバックアップ（版 032）を復元するときは、RC4 のイメージで動かす
