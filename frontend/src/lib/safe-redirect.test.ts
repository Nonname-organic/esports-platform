import { safeNextPath } from "./safe-redirect";

const ORIGIN = "https://axelia.example";
const FALLBACK = "/dashboard";

const ALLOWED: Array<[string, string]> = [
  ["/dashboard", "/dashboard"],
  ["/tournaments/abc", "/tournaments/abc"],
  ["/teams/1?tab=members#roster", "/teams/1?tab=members#roster"],
  ["/a/../matches/1", "/matches/1"],
  // エンコードされた "/" や "\" はパスの文字のまま（このサイトの存在しないページになるだけ）
  ["/%2F%2Fexample.com", "/%2F%2Fexample.com"],
  ["/%5Cexample.com", "/%5Cexample.com"],
  ["/javascript:alert(1)", "/javascript:alert(1)"],
];

const REJECTED: Array<string | null | undefined> = [
  null,
  undefined,
  "",
  "dashboard",
  // 別ホスト（プロトコル相対・バックスラッシュ・絶対 URL）
  "//example.com",
  "///example.com",
  "/\\example.com",
  "\\\\example.com",
  "/\\/example.com",
  "https://example.com/path",
  "HTTPS://EXAMPLE.COM",
  "http:example.com",
  // スクリプト・データ URL
  "javascript:alert(1)",
  "JaVaScRiPt:alert(document.cookie)",
  " javascript:alert(1)",
  "data:text/html,<script>alert(1)</script>",
  "vbscript:msgbox(1)",
  // タブ・改行・空白（ブラウザが取り除くと "//host" になる）
  "/\t/example.com",
  "/\n/example.com",
  "/\r\n/example.com",
  "\t//example.com",
  " /dashboard",
  "/dash board",
  "/\u0000/example.com",
  // 正規化すると "//host" になるパス
  "/.//example.com",
  "/..//example.com",
  "/%2e//example.com",
  "/a/..//example.com",
  // URL エンコード（1 回・2 回）で "/" を隠した値
  "%2F%2Fexample.com",
  "%252F%252Fexample.com",
  // ログイン・登録へ戻すとループになる
  "/login",
  "/register",
  "/login?next=//example.com",
];

const TOO_LONG = "/" + "a".repeat(2048);

describe("ログイン後の転送先（?next=）", () => {
  it.each(ALLOWED)("同じサイトの相対パスは通す: %s", (raw, expected) => {
    expect(safeNextPath(raw)).toBe(expected);
  });

  it.each(REJECTED.map((v) => [v]))("外部・不正な値は既定のページにする: %j", (raw) => {
    expect(safeNextPath(raw)).toBe(FALLBACK);
  });

  it("長すぎる値（2049 文字）は通さない", () => {
    expect(safeNextPath(TOO_LONG)).toBe(FALLBACK);
  });

  it("クエリ文字列から読んだ値（1 回デコード済み）でも外へ出ない", () => {
    const fromQuery = (qs: string) => safeNextPath(new URLSearchParams(qs).get("next"));
    expect(fromQuery("next=%2F%2Fexample.com")).toBe(FALLBACK);
    expect(fromQuery("next=%2F%5Cexample.com")).toBe(FALLBACK);
    expect(fromQuery("next=%2F%09%2Fexample.com")).toBe(FALLBACK);
    expect(fromQuery("next=javascript%3Aalert(1)")).toBe(FALLBACK);
    expect(fromQuery("next=%252F%252Fexample.com")).toBe(FALLBACK);
    expect(fromQuery("next=%2Ftournaments%2Fabc")).toBe("/tournaments/abc");
  });

  it("どの値でも、最終的な遷移先は同じオリジンの http(s) のページ", () => {
    for (const raw of [...ALLOWED.map(([r]) => r), ...REJECTED, TOO_LONG]) {
      const target = new URL(safeNextPath(raw), ORIGIN);
      expect(target.origin).toBe(ORIGIN);
      expect(target.protocol).toBe("https:");
    }
  });
});
