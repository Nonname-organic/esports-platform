# ドキュメント（PDF）

利用者向けと管理者向けのPDFを、スクリプトから生成します。

| ファイル | 対象 | 内容 |
|---|---|---|
| `AXELIA_操作マニュアル.pdf` | 参加者・主催者 | 登録から大会参加・大会運営までの操作手順 |
| `AXELIA_運用手順書.pdf` | 管理者 | 構成・デプロイ・環境変数・バックアップ・障害対応 |

## 生成方法

```bash
pip install reportlab
python docs/manual/build_manual.py
python docs/manual/build_ops_guide.py
```

Windows 同梱の游ゴシックを埋め込みます（無い場合はメイリオ→MSゴシックへ退避）。

## 構成

- `pdf_builder.py` — 組版の部品（見出し・手順・表・囲み・目次・禁則処理）
- `build_manual.py` — 操作マニュアルの本文
- `build_ops_guide.py` — 運用手順書の本文

本文を修正したら、対応する `build_*.py` を再実行してください。目次のページ番号と
総ページ数は2パス方式で自動的に振り直されます。

## 画面キャプチャについて

現在は「［ 画面キャプチャ ］」の枠とキャプションだけを配置しています。
実画面の画像を差し込む場合は `pdf_builder.py` の `figure()` を、
`canvas.drawImage()` を使う実装に差し替えてください。
