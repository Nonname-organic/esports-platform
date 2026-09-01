"""AXELIA 運用手順書（管理者向け）のPDFを生成する。

    python docs/manual/build_ops_guide.py

秘密情報（APIキー・DBパスワード）は本文に載せない。配布される可能性がある
ドキュメントに実値を書かず、取得場所だけを示す方針とする。
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_builder import Doc, TocEntry  # noqa: E402

SITE_URL = "https://amazing-froyo-1cab9c.netlify.app"
API_URL = "https://axelia-api.onrender.com"
REPO = "Nonname-organic/esports-platform"
CONTACT = "info@axelia-esports.jp"
VERSION = "1.0"
DATE = "2026年9月1日"
DOC_TITLE = "運用手順書"


def build(doc: Doc, toc_offset: int) -> None:
    # ══ 1 システム構成 ══════════════════════════════════════════════════════
    doc.h1("1", "システム構成")
    doc.para(
        "本書は AXELIA を運用・保守する管理者向けの手順書です。"
        "デプロイ、設定変更、バックアップ、障害時の対応をまとめています。"
    )

    doc.h2("1-1", "全体像")
    doc.para(
        "フロントエンド・API・データベース・キャッシュを、それぞれ無料枠のある"
        "サービスに分けて構成しています。いずれもクレジットカードの登録は不要です。"
    )
    doc.table(
        ["役割", "サービス", "内容"],
        [
            ["フロントエンド", "Netlify", "画面表示。/api/* へのアクセスをAPIへ中継"],
            ["API", "Render", "FastAPI。スコアボードOCRと定期処理を同一プロセスで実行"],
            ["データベース", "Neon", "PostgreSQL。大会・チーム・戦績のすべてを保持"],
            ["キャッシュ・キュー", "Upstash", "Redis。通知配信とキャッシュに使用"],
            ["メール送信", "Resend", "パスワード再設定メールの配信"],
            ["ソース管理", "GitHub", f"{REPO}"],
        ],
        widths=[22, 16, 62],
    )

    doc.h2("1-2", "無料枠の制約")
    doc.para("運用にあたって把握しておくべき制約です。")
    doc.table(
        ["制約", "影響と対応"],
        [
            [
                "APIの休止",
                "15分間アクセスがないとAPIが休止します。次のアクセスで自動的に"
                "復帰しますが、最初の1回だけ30〜60秒かかります。"
                "人に見せる直前に一度アクセスしておくと回避できます。",
            ],
            [
                "アップロード画像が消える",
                "APIの再デプロイでアップロード済みの画像が失われます。"
                "データベースの内容（大会・戦績）は影響を受けません。"
                "画像を永続化する場合は Cloudflare R2 等の外部ストレージを設定してください。",
            ],
            [
                "OCRのメモリ",
                "スコアボード解析はメモリを多く使います。稀に失敗する場合は"
                "少し時間をおいて再実行してください。",
            ],
        ],
        widths=[24, 76],
    )

    doc.h2("1-3", "アクセス情報")
    doc.table(
        ["対象", "URL"],
        [
            ["サービス（フロント）", SITE_URL],
            ["API", API_URL],
            ["APIの稼働確認", f"{API_URL}/health/ready"],
            ["ソースコード", f"https://github.com/{REPO}"],
        ],
        widths=[28, 72],
    )
    doc.callout(
        "管理コンソール",
        "Netlify・Render・Neon・Upstash・Resend の各ダッシュボードには、"
        "GitHubアカウントまたは登録済みメールアドレスでログインします。"
        "接続文字列やAPIキーの実値は各ダッシュボードで確認してください"
        "（本書には記載していません）。",
        kind="info",
    )

    # ══ 2 デプロイ ═══════════════════════════════════════════════════════════
    doc.h1("2", "デプロイ")

    doc.h2("2-1", "デプロイの流れ")
    doc.para(
        "GitHub の main ブランチへの push をきっかけに、"
        "Netlify と Render が自動でビルド・デプロイします。"
        "手動でのファイル転送は不要です。"
    )
    doc.steps([
        "ローカルで変更をコミットします。",
        "git push origin main を実行します。",
        "Netlify と Render がそれぞれビルドを開始します（3〜6分）。",
        "両方の完了を確認し、サイトで動作を確認します。",
    ])
    doc.callout(
        "デプロイ中も旧バージョンが動き続けます",
        "ビルドが完了するまで、利用者には従来のバージョンが表示されます。"
        "ビルドに失敗した場合も、稼働中のバージョンはそのまま維持されます。",
        kind="info",
    )

    doc.h2("2-2", "ビルド結果の確認")
    doc.table(
        ["対象", "確認場所"],
        [
            ["フロント", "Netlify ダッシュボード → Deploys タブ"],
            ["API", "Render ダッシュボード → axelia-api → Logs / Events"],
        ],
        widths=[20, 80],
    )
    doc.para("API が正常に起動していれば、次のログが出ます。")
    doc.bullets([
        "== migration ==（データベースのマイグレーション実行）",
        "== starting api ==（APIの起動）",
        "Uvicorn running on http://0.0.0.0:10000",
    ])

    doc.h2("2-3", "設定ファイル")
    doc.table(
        ["ファイル", "役割"],
        [
            ["netlify.toml", "フロントのビルド設定・API中継・検索エンジン除外ヘッダー"],
            ["render.yaml", "APIのビルド設定・環境変数の定義"],
            ["backend/start.sh", "APIの起動手順（マイグレーション → 起動）"],
        ],
        widths=[26, 74],
    )
    doc.callout(
        "ビルド設定はリポジトリ側が優先です",
        "Netlify・Render のダッシュボードで設定を変更するより、"
        "netlify.toml・render.yaml を編集して push する方が確実です。"
        "設定が二重管理にならないよう、ダッシュボード側は空欄のままにしてあります。",
        kind="warn",
    )

    # ══ 3 環境変数 ═══════════════════════════════════════════════════════════
    doc.h1("3", "環境変数")
    doc.para(
        "秘密情報を含むため、値は各ダッシュボードで設定します。"
        "変更後は自動で再起動・再デプロイされます。"
    )

    doc.h2("3-1", "API（Render）")
    doc.table(
        ["変数名", "内容"],
        [
            ["DATABASE_URL", "Neon の接続文字列。※ pooler ではない方を使用"],
            ["REDIS_URL", "Upstash の接続文字列（rediss:// で始まる）"],
            ["SECRET_KEY", "トークン署名用の秘密鍵。変更すると全員がログアウトされます"],
            ["FRONTEND_BASE_URL", "フロントの公開URL。メール内リンクの基点になります"],
            ["ALLOWED_ORIGINS", "アクセスを許可するオリジン。通常はフロントのURL"],
            ["SMTP_PASSWORD", "Resend のAPIキー"],
            ["RUN_WORKER_IN_APP", "true。通知・自動処理をAPI内で動かす設定"],
            ["EXPOSE_API_DOCS", "false。APIドキュメントの公開可否"],
        ],
        widths=[28, 72],
    )
    doc.callout(
        "DATABASE_URL は pooler を使わないこと",
        "Neon はホスト名に -pooler が付いた接続文字列も発行しますが、"
        "本サービスのデータベースドライバとは相性が悪く、正しく動作しません。"
        "-pooler が付かない方（direct connection）を使用してください。",
        kind="warn",
    )

    doc.h2("3-2", "フロント（Netlify）")
    doc.table(
        ["変数名", "内容"],
        [
            ["INTERNAL_API_URL", "サーバー側からAPIを呼ぶときのURL"],
            ["NEXT_PUBLIC_WS_URL", "リアルタイム更新の接続先（wss:// で始まる）"],
            ["NEXT_PUBLIC_DEMO_MODE", "true でデモ告知バナーを表示"],
        ],
        widths=[30, 70],
    )
    doc.callout(
        "フロントの環境変数は再デプロイが必要です",
        "NEXT_PUBLIC_ で始まる変数はビルド時に埋め込まれます。"
        "値を変更したら、Deploys タブから再デプロイしてください。",
        kind="warn",
    )

    # ══ 4 データベース ═══════════════════════════════════════════════════════
    doc.h1("4", "データベース")

    doc.h2("4-1", "マイグレーション")
    doc.para(
        "データベースの構造変更は、APIの起動時に自動で適用されます"
        "（backend/start.sh 内の alembic upgrade head）。"
        "デプロイ後に手動で実行する必要はありません。"
    )

    doc.h2("4-2", "バックアップ")
    doc.para(
        "定期的に手元へバックアップを取得しておくことを推奨します。"
        "下記のコマンドは Docker が動作する環境で実行します。"
        "PostgreSQL のバージョンを Neon 側と合わせる必要があります。"
    )
    doc.steps([
        "Neon ダッシュボードから接続文字列を取得します。",
        "下記コマンドの <接続文字列> を置き換えて実行します。",
        "生成された .sql.gz ファイルを安全な場所に保管します。",
    ])
    doc.callout(
        "バックアップ取得コマンド",
        "docker run --rm postgres:18-alpine pg_dump \"<接続文字列>\" "
        "--clean --if-exists --no-owner | gzip -9 > axelia-backup.sql.gz",
        kind="info",
    )
    doc.para(
        "Neon のダッシュボードには、過去の状態へ戻すための履歴機能もあります"
        "（保持期間はプランによります）。あわせて確認してください。"
    )

    doc.h2("4-3", "復元")
    doc.callout(
        "復元コマンド",
        "gzip -dc axelia-backup.sql.gz | docker run --rm -i postgres:18-alpine "
        "psql \"<接続文字列>\" -v ON_ERROR_STOP=1",
        kind="info",
    )
    doc.callout(
        "復元は現在のデータを上書きします",
        "実行前に、現在の状態のバックアップを取得しておいてください。"
        "また、復元中はAPIを停止しておくと安全です"
        "（Render ダッシュボードの Suspend から一時停止できます）。",
        kind="warn",
    )

    doc.h2("4-4", "動作確認")
    doc.para(
        "バックアップは、復元できて初めてバックアップです。"
        "定期的に、別のデータベースへ復元して内容を確認することを推奨します。"
    )

    # ══ 5 メール送信 ═════════════════════════════════════════════════════════
    doc.h1("5", "メール送信")
    doc.para(
        "パスワード再設定メールは Resend 経由で送信します。"
        "送信元は noreply@axelia-esports.jp です。"
    )

    doc.h2("5-1", "設定状況")
    doc.table(
        ["項目", "状態"],
        [
            ["ドメイン認証", "axelia-esports.jp を登録済み（SPF・DKIM 設定済み）"],
            ["送信元アドレス", "noreply@axelia-esports.jp"],
            ["無料枠", "100通/日・3,000通/月"],
        ],
        widths=[26, 74],
    )

    doc.h2("5-2", "送信テスト")
    doc.para("ローカル環境で、設定内容の確認とテスト送信ができます。")
    doc.callout(
        "テスト送信コマンド",
        "docker compose exec api python scripts/send_test_email.py 宛先アドレス",
        kind="info",
    )

    doc.h2("5-3", "メールが届かない場合")
    doc.bullets([
        "迷惑メールフォルダを確認する",
        "Resend ダッシュボードの Logs で送信結果を確認する",
        "Render の環境変数 SMTP_PASSWORD が正しいAPIキーか確認する",
        "FRONTEND_BASE_URL が実際の公開URLと一致しているか確認する",
    ])

    # ══ 6 監視と障害対応 ═════════════════════════════════════════════════════
    doc.h1("6", "監視と障害対応")

    doc.h2("6-1", "稼働確認")
    doc.para("APIの状態は、次のURLで確認できます。")
    doc.table(
        ["URL", "内容"],
        [
            [f"{API_URL}/health", "APIプロセスが動作しているか"],
            [f"{API_URL}/health/ready", "データベース・キャッシュに接続できているか"],
        ],
        widths=[46, 54],
    )
    doc.para(
        "/health/ready が {\"status\":\"ready\"} を返せば正常です。"
        "database または cache が error の場合、接続情報を確認してください。"
    )

    doc.h2("6-2", "よくある障害と対処")
    doc.table(
        ["症状", "原因と対処"],
        [
            [
                "サイトは開くが操作でエラーになる",
                "APIが休止から復帰中の可能性があります。1分ほど待って再読み込みしてください。"
                "改善しない場合は /health/ready を確認します。",
            ],
            [
                "/health/ready の database が error",
                "Neon が休止しているか、接続文字列が誤っています。"
                "Neon ダッシュボードでデータベースの状態と接続文字列を確認してください。",
            ],
            [
                "/health/ready の cache が error",
                "Upstash の接続文字列を確認してください。"
                "無料枠の上限に達している場合もダッシュボードに表示されます。",
            ],
            [
                "デプロイが失敗する",
                "Netlify / Render のビルドログを確認します。"
                "依存パッケージの脆弱性でブロックされる場合があり、"
                "その際はログに指示された版へ更新して push します。",
            ],
            [
                "通知が届かない",
                "RUN_WORKER_IN_APP が true になっているか確認してください。"
                "false の場合、通知処理が動作しません。",
            ],
        ],
        widths=[30, 70],
    )

    doc.h2("6-3", "ログの確認")
    doc.table(
        ["対象", "場所"],
        [
            ["API のログ", "Render ダッシュボード → axelia-api → Logs"],
            ["ビルドログ", "Netlify → Deploys / Render → Events"],
            ["メール送信結果", "Resend ダッシュボード → Logs"],
        ],
        widths=[24, 76],
    )

    # ══ 7 公開範囲の変更 ═════════════════════════════════════════════════════
    doc.h1("7", "限定公開から一般公開へ")
    doc.para(
        "現在は、URLを知っている人だけが閲覧できる限定公開の状態です。"
        "検索エンジンには表示されません。一般公開に切り替える場合は、"
        "次の3か所の設定を解除します。"
    )
    doc.table(
        ["ファイル", "変更内容"],
        [
            ["frontend/src/app/robots.ts", "disallow を allow に変更"],
            ["frontend/src/app/layout.tsx", "robots: { index: false } の行を削除"],
            ["frontend/next.config.ts", "X-Robots-Tag のヘッダー行を削除"],
        ],
        widths=[36, 64],
    )
    doc.para("あわせて、デモ告知バナーを消す場合は次の設定を変更します。")
    doc.bullets([
        "Netlify の環境変数 NEXT_PUBLIC_DEMO_MODE を false にする",
    ])
    doc.callout(
        "一般公開の前に確認すること",
        "サンプルとして投入したデモデータ（大会・チーム・戦績）が残っていないか、"
        "利用規約・プライバシーポリシーの内容が実態と合っているかを確認してください。"
        "URL・データ・構成はそのまま引き継げます。",
        kind="warn",
    )

    doc.h2("7-1", "独自ドメインを使う場合")
    doc.para(
        "axelia-esports.jp のサブドメイン（例: demo.axelia-esports.jp）を"
        "割り当てることができます。ネームサーバーの変更は不要です。"
    )
    doc.steps([
        "Netlify のプロジェクト設定で Domain management を開きます。",
        "Add a domain から使用するサブドメインを入力します。",
        "表示された値を、ムームードメインのDNS設定に CNAME として追加します。",
        "反映後、証明書は自動で発行されます。",
        "Render の環境変数 FRONTEND_BASE_URL と ALLOWED_ORIGINS を新しいURLに変更します。",
    ])

    # ══ 8 ローカル開発環境 ═══════════════════════════════════════════════════
    doc.h1("8", "ローカル開発環境")
    doc.para(
        "手元で動作を確認する場合は、Docker Compose で一式を起動できます。"
        "クラウド側の設定には影響しません。"
    )
    doc.callout(
        "起動コマンド",
        "docker compose up -d --build",
        kind="info",
    )
    doc.table(
        ["用途", "コマンド"],
        [
            ["起動", "docker compose up -d --build"],
            ["停止", "docker compose down"],
            ["APIログ", "docker compose logs api --tail 50"],
            ["マイグレーション", "docker compose exec api alembic upgrade head"],
            ["メール送信テスト", "docker compose exec api python scripts/send_test_email.py <宛先>"],
        ],
        widths=[24, 76],
    )
    doc.para(f"起動後、ブラウザで http://localhost を開きます。")

    # ══ 9 問い合わせ ═════════════════════════════════════════════════════════
    doc.h1("9", "問い合わせ先")
    doc.para("本書の内容やシステムに関するご相談は、下記までご連絡ください。")
    doc.callout("連絡先", CONTACT, kind="info")


def main() -> None:
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "AXELIA_運用手順書.pdf")
    tmp_path = os.path.join(out_dir, "_ops_pass1.pdf")

    probe = Doc(tmp_path, DOC_TITLE, header_title=f"AXELIA {DOC_TITLE}")
    probe.enable_chrome()
    build(probe, toc_offset=0)
    probe.save()
    entries = probe.toc_entries
    body_pages = probe.page

    toc_pages = max(1, math.ceil(len(entries) / 32))
    offset = 1 + toc_pages
    shifted = [TocEntry(e.number, e.title, e.page + offset, e.level) for e in entries]
    total = body_pages + offset

    doc = Doc(out_path, DOC_TITLE, header_title=f"AXELIA {DOC_TITLE}")
    doc._total_pages = total
    doc.title_page(
        product="AXELIA",
        tagline="VALORANT 大会プラットフォーム",
        description=(
            "システム構成・デプロイ・設定変更・バックアップ・障害対応をまとめた"
            "管理者向けの手順書です。"
        ),
        version=VERSION,
        date=DATE,
        contact=CONTACT,
    )
    doc.enable_chrome()
    doc.render_toc(shifted)
    doc.new_page()
    doc.toc_entries = []
    build(doc, toc_offset=offset)
    doc.save()

    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    print(f"生成: {out_path}")
    print(f"  ページ数: {doc.page} / 目次項目: {len(entries)}")


if __name__ == "__main__":
    main()
