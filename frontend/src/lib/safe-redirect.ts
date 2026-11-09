const FALLBACK = "/dashboard";
// 相対パスを解釈するためだけの仮のオリジン（遷移先には使わない）
const BASE = "http://internal.invalid";

// ブラウザは URL 中のタブ・改行を捨て、"\" を "/" とみなす。解釈が変わる文字は最初から通さない
const hasUnsafeChar = (s: string) => Array.from(s).some((ch) => ch <= " " || ch === "\u007f" || ch === "\\");

/**
 * ログイン後の転送先（?next=）を検証する。
 *
 * 同じサイト内の相対パスだけを通し、それ以外（//host・絶対 URL・javascript: など）は
 * 既定のページにする。外部サイトへの転送と、URL に仕込んだスクリプトの実行を防ぐ。
 */
export function safeNextPath(raw: string | null | undefined): string {
  if (!raw || raw.length > 2048 || !raw.startsWith("/") || hasUnsafeChar(raw)) return FALLBACK;
  let url: URL;
  try {
    url = new URL(raw, BASE);
  } catch {
    return FALLBACK;
  }
  const path = url.pathname + url.search + url.hash;
  // "/.//host" は正規化すると "//host"（別ホスト）になるので、正規化した後でも確かめる
  if (url.origin !== BASE || path.startsWith("//")) return FALLBACK;
  if (url.pathname === "/login" || url.pathname === "/register") return FALLBACK;
  return path;
}
