/**
 * 公開URLの基点。
 *
 * canonical・OGP・sitemap が同じ値を使う必要があるため1箇所に置く。
 * 環境変数で上書きできるようにしてあるのは、プレビュー環境や
 * ドメイン変更のときに全ファイルを書き換えずに済ませるため。
 */
export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ??
  "https://app.axelia-esports.jp";
