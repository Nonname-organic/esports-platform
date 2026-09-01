# ドキュメント（PDF）

利用者向けと管理者向けのPDFを、スクリプトから生成します。

| ファイル | 対象 | 内容 |
|---|---|---|
| `AXELIA_操作マニュアル.pdf` | 参加者・主催者 | 登録から大会参加・大会運営までの操作手順 |
| `AXELIA_運用手順書.pdf` | 管理者 | 構成・デプロイ・環境変数・バックアップ・障害対応 |

## 生成方法

```bash
pip install reportlab pillow
python docs/manual/build_manual.py
python docs/manual/build_ops_guide.py
```

Windows 同梱の游ゴシックを埋め込みます（無い場合はメイリオ→MSゴシックへ退避）。

## 構成

- `pdf_builder.py` — 組版の部品（見出し・手順・表・囲み・図・目次・禁則処理）
- `build_manual.py` — 操作マニュアルの本文
- `build_ops_guide.py` — 運用手順書の本文
- `capture_figures.py` — 画面キャプチャの撮影スクリプト
- `figures/` — 撮影済みのPNG（本文から参照）

本文を修正したら、対応する `build_*.py` を再実行してください。目次のページ番号と
総ページ数は2パス方式で自動的に振り直されます。

## 画面キャプチャの撮り直し

画面を変更したら、ローカルのスタックを起動した状態で撮り直します。

```bash
docker compose up -d
AXELIA_CAPTURE_PW=<デモ用アカウントのパスワード> python docs/manual/capture_figures.py
python docs/manual/build_manual.py
```

Playwright（`pip install playwright`）から、PCにインストール済みの Chrome を
2倍解像度で動かして `figures/` に書き出します。ブラウザのダウンロードは不要です。

撮影には次のデモ用アカウントを使います。無い場合は先に作成してください。

| アカウント | 役割 | 用途 |
|---|---|---|
| `kaito.demo@axelia-demo.example.com`（Kaito_VLR） | player | エントリー・チェックインの画面 |
| `staff.demo@axelia-demo.example.com`（AXELIA_Staff） | organizer | 大会作成・試合管理の画面 |

チェックイン受付中の画面を撮るために、スクリプトが大会のチェックイン時間を一時的に
書き換え、撮影後に元へ戻します（`capture_figures.py` の `main()` を参照）。

紙面に貼るときは `pdf_builder.py` の `FIGURE_PPP`（既定 3.0 ≒ 216dpi）まで
自動で縮小されます。PDFが重くなる場合はこの値を下げてください。
