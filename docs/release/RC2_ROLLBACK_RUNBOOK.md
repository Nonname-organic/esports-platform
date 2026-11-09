# RC2 切り戻しの手順（ConoHa VPS）

- 作成: 2026-11-09（RC2 統合・必須修正工程）。**本番ではどれも未実行**
- 方針: **イメージだけを、版（タグ）と digest を明示して戻す。DB は戻さない**（`alembic downgrade` を使わない）
- phase10 の「直近の Deploy を再実行する」は使えない。Deploy workflow が無効の間は再実行できず、再実行できるのも最初の実行から 30 日まで
  （直近の成功 `38190818029` は 2026-10-12 01:09 UTC の実行なので、2026-11-11 ごろで期限が切れる）
- 手で `up` するのは phase10 の「手で up しない」の例外になる。版と digest を `config --images` で確かめてから行う

## 1. 前提（デプロイの前に控えておくもの）

[デプロイ手順](RC2_DEPLOYMENT_RUNBOOK.md)の 3 で作った `~/rollback-images.yml`（稼働していた 4 サービスのイメージを digest で指定したもの）。

```yaml
services:
  api:
    image: ghcr.io/nonname-organic/esports-platform-api@sha256:<api の digest>
  worker:
    image: ghcr.io/nonname-organic/esports-platform-worker@sha256:<worker の digest>
  scheduler:
    image: ghcr.io/nonname-organic/esports-platform-api@sha256:<api の digest>
  frontend:
    image: ghcr.io/nonname-organic/esports-platform-frontend@sha256:<frontend の digest>
```

- compose の `IMAGE_TAG` は api・worker・frontend で共通なので、`IMAGE_TAG` だけでは 3 つの digest を固定できない。このファイルを compose に重ねて、サービスごとに固定する
- 重ねたときの描画（4 サービスがそれぞれの digest になり、scheduler は api と同じ）は、リポジトリの compose でローカルに確かめた
- このファイルが無い、または digest が取れなかった場合は、タグ（`sha-c0a80ad`）で戻し、取得したイメージの digest を作業記録に残す

## 2. 戻すかどうかの判断

[デプロイ手順](RC2_DEPLOYMENT_RUNBOOK.md)の 8 章の止める条件に当たり、設定の直し（`.env` など）で解決しないときに戻す。戻すことにも承認が要る。

| 状況 | 対応 |
|---|---|
| 先行マイグレーション（デプロイ手順 5）が失敗した | 戻さない。版は 027 のまま、旧コードも動いている。原因を調べる |
| Deploy の入れ替え前の検査で止まった | 戻さない。旧コードのまま動いている。設定を直す |
| 入れ替えた後に readiness が通らない、5xx が続く | 戻す（3 章） |
| 特定の機能だけの不具合で、データを壊していない | 修正版を出すか、戻すかを判断する |

## 3. 手順

```bash
cd /opt/app
# 1. 同じ版の再デプロイを防ぐ
gh workflow disable deploy-demo.yml --repo Nonname-organic/esports-platform

# 2. 状態を控える
docker compose ps
docker compose exec -T postgres psql -U esports_user -d esports_db -tAc 'select version_num from alembic_version'
for q in match_events notification_events analytics_events discord_events; do
  printf '%s: ' "$q"; docker compose exec -T redis redis-cli LLEN "queue:$q"
done

# 3. 控えた digest を compose に重ねる（このシェルの中だけ）
export COMPOSE_FILE="$(grep '^COMPOSE_FILE=' .env | cut -d= -f2-):$HOME/rollback-images.yml"
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
docker compose exec -T postgres psql -U esports_user -d esports_db -tAc 'select version_num from alembic_version'   # 030 のまま

unset COMPOSE_FILE IMAGE_ORG IMAGE_TAG
```

- **旧イメージの中で `alembic` を実行しない。** 旧コードは 030 を知らないので「Can't locate revision identified by '030'」で失敗する。版は psql で見る
- 2 のキューが空でなければ、処理が終わるのを待ってから 4 に進む。新しいコードが積んだ、旧 worker の知らない種類のイベント（辞退・利用停止・ロール変更の監査など）を、旧 worker がどう扱うかは確かめていない
- nginx・postgres・redis は入れ替えない（RC2 の設定のままで旧コードは動く。アップロードの上限 11m もそのままでよい）

## 4. 完了の判定

- [ ] 4 サービスが控えた digest（`docker inspect` の結果が `…@sha256:…`）
- [ ] readiness が 200、`docker compose ps` で api が healthy
- [ ] ログイン・大会一覧・詳細・試合ページが開く
- [ ] 5xx が増えない（色の制御文字を除いて数える。[チェックリスト](RC2_PRODUCTION_CHECKLIST.md)の 5 章）
- [ ] `alembic_version` は 030 のまま

## 5. 戻せないときに止める条件

次のどれかが起きたら、手で直そうとせずに止める。バックアップからの復元を含めて判断する（承認が要る。復元するとバックアップ以降の書き込みが消える）。

- 旧イメージを取得できない（GHCR から消えた、ログインできない）
- 旧イメージで readiness が通らない
- ログに、旧コードが知らない列・表のエラーが続く

## 6. DB を戻さない理由と、旧コードで動かした間のデータ

旧コード（027 まで）は 030 のスキーマで動く。028〜030 は表と列の追加・拡張とデータの補正だけで、旧コードが使う表・列を消したり変えたりしていない。
（旧コードを 030 の DB で起動し、主要な API が応答することを、使い捨ての環境で確かめた。本番では未実施）

`alembic downgrade` を使わない理由:
- `downgrade 027` は 030・029・028 をまとめて戻す。029 の表（結果報告）が消えるので、RC2 に戻したときに結果の登録がすべて 500 になる
- 030 を戻すには `player_seeks` の投稿を消す必要があり、応募（`recruitment_applications`）が連鎖して消え、元に戻せない

旧コードで動かした間に書かれるデータ:

| 書き込み | RC2 に戻したときに正しいか | 対応 |
|---|---|---|
| 非公開・限定公開で作った大会 | **正しくない**。旧版の作成画面は `rules` にしか書かず、列は `public` のまま | 7 章の SQL で直す |
| 編集した大会（列と `rules` の両方を書く） | 正しい | なし |
| 028 で補正済みの大会 | 正しい（旧版の一覧は公開範囲を見ないので、その間は一覧に出る） | なし |
| 確認待ち・異議中の報告がある試合への、主催者の結果登録 | 結果は正しい。報告は、確定した試合に開いたまま残る（旧コードは報告の表を知らない） | 7 章の SQL で閉じる |
| 募集（`player_seeks` を含む）と応募、大会・試合・チーム・利用者の削除 | 正しい | なし |

## 7. RC2 に戻した後（再デプロイの後）に流す SQL

RC2 のイメージに戻して readiness が通った後に、1 回流す。何度流しても結果は同じ。

```bash
cd /opt/app
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U esports_user -d esports_db <<'SQL'
BEGIN;
-- 旧コードの間に「非公開」「限定公開」で作られた大会を直す。直す前の値は 028 の退避表に残す
INSERT INTO tournament_visibility_backup_028 (tournament_id, previous_visibility, new_visibility)
SELECT id, visibility, rules->>'visibility' FROM tournaments
 WHERE visibility = 'public' AND rules->>'visibility' IN ('limited', 'private')
ON CONFLICT (tournament_id) DO NOTHING;
UPDATE tournaments SET visibility = rules->>'visibility'
 WHERE visibility = 'public' AND rules->>'visibility' IN ('limited', 'private');
-- 旧コードで結果が確定した試合に残った、確認待ち・異議中の報告を閉じる（RC2 が確定時に行うのと同じ扱い）
UPDATE match_result_reports r SET status = 'superseded'
  FROM matches m
 WHERE m.id = r.match_id AND m.status IN ('completed', 'forfeit') AND r.status IN ('pending', 'disputed');
COMMIT;
SQL
```

- **028 の UPDATE をそのまま流し直さない。** 028 の UPDATE は「列が補正前の値（`public`）のままなら直す」条件なので、旧コードの間に主催者が
  編集画面で公開へ戻した大会（列も `rules` も `public`）を、非公開に戻してしまう。上の SQL は「列が `public` で `rules` が非公開・限定公開」
  の行だけを直すので、編集済みの大会は変わらない
- 上の大会の補正は、使い捨ての DB で確かめた（旧コードの作成画面で作った大会は直り、編集済みの大会は反転せず、2 回目は何も変わらない。
  対照として、028 の UPDATE をそのまま流すと編集済みの大会が非公開に戻ることも確かめた）
- 大会の公開範囲を個別に直すときは、SQL ではなく主催者か管理者が編集画面で設定し直す（列と `rules` の両方が書かれる）

## 8. RC2 の後の版から RC2 へ戻す場合

同じ手順でよい。次の版をデプロイする前に、その時点の RC2 のイメージで `~/rollback-images.yml` を作り直しておく。
次の版にマイグレーションが含まれる場合は、RC2 のコードがそのスキーマで動くかを、その版の工程で確かめる。
