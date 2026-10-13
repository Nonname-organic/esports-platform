/**
 * 公開ページの文言が方針どおりかを、ソースを読んで確かめる。
 *
 * 決めてあること:
 *   - デモ環境であることの告知は「これはデモ環境です」に統一し、
 *     「公開」＋「準備中」をつないだ表現は使わない。
 *   - 大会の開催状況は主語を「運営」にする。利用者自身は主催者機能を
 *     有効にすれば大会を作れるので、主語を省くと禁止されていると読める。
 *   - 実装済みだがデータが無いと結果が出ない機能を「提供予定」と書かない。
 *
 * 文言は人が触るので、方針から外れたときに気づけるようにしておく。
 * DOM を起こす必要はないので testEnvironment は既定の node のまま
 * （jest-environment-jsdom を入れずに済む形にしてある）。
 *
 * 検査対象はここに列挙した分だけに限る。リポジトリ全体を走査すると、
 * 設計の記録や過去の経緯を書いたドキュメントで落ちるようになる。
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

const SRC = join(__dirname, "..");

/** 文言の検査対象。このテスト自身は入れない（禁止語を自分が含むため）。 */
const TARGETS = [
  "app/layout.tsx",
  "app/robots.ts",
  "app/sitemap.ts",
  "components/live/preparing-notice.tsx",
  "components/live/landing-live.tsx",
  "components/hero/floating-live-cards.tsx",
];

// 直接書くとこのファイル自体が禁止語を含むことになるので組み立てる。
// 検査対象に加えられても自己一致しない。
const RETIRED = ["公開", "準備中"].join("");
const RETIRED_HEADING = ["提供予定", "（準備中）"].join("");

const NOTICE = "components/live/preparing-notice.tsx";
const BANNER_FILE = "components/demo-banner.tsx";
const LAYOUT = "app/layout.tsx";

const BADGE = "デモ環境";
const BANNER = "これはデモ環境です";
const OPERATOR = "運営";

const read = (rel: string) => readFileSync(join(SRC, rel), "utf8");

/**
 * JSDoc・行コメント・JSX コメントを落とす。
 *
 * バッジの検査でコメントを残すと、JSDoc の「デモ環境である旨の告知」や
 * コメントアウトされた JSX でも通ってしまう。
 */
const stripComments = (src: string) =>
  src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^[ \t]*\/\/.*$/gm, "");

/** 要素の中身が BADGE だけであること。タグ名とインデントには依存しない。 */
const BADGE_AS_TEXT = new RegExp(`<[a-zA-Z][^>]*>\\s*${BADGE}\\s*</`);

describe("デモ環境の文言", () => {
  it.each(TARGETS)("%s に廃止した表現が残っていない", (rel) => {
    expect(read(rel)).not.toContain(RETIRED);
  });

  it("トップのバッジがデモ環境であることを示す", () => {
    // コメントを落としてから、要素の中身として出ていることを見る。
    // 単に文字列を数えると JSDoc だけでも通ってしまう
    expect(stripComments(read(NOTICE))).toMatch(BADGE_AS_TEXT);
  });

  it("全ページに出る告知が「これはデモ環境です」である", () => {
    expect(read(BANNER_FILE)).toContain(BANNER);
  });

  it("実装済みの機能に旧見出しを使っていない", () => {
    // 4項目はいずれも実装済みで、対象データが無いだけ。「提供予定」は事実と違う
    expect(read(NOTICE)).not.toContain(RETIRED_HEADING);
  });

  it("大会作成の利用条件が書かれている", () => {
    expect(read(NOTICE)).toContain("主催者機能を有効にすると");
  });

  it("大会・試合データに依存する機能が別枠になっている", () => {
    const notice = read(NOTICE);
    expect(notice).toContain("大会を作成すると使える機能");
    expect(notice).toContain("大会と試合のデータが必要");
  });

  it("大会の開催状況は運営を主語にしていて、利用者自身の作成と矛盾しない", () => {
    // 主語を省くと「利用者も大会を作れない」と読める
    const notice = read(NOTICE);
    expect(notice).toContain(`${OPERATOR}が主催する大会は開催していません`);
    expect(notice).toContain(`${OPERATOR}としての参加者の募集も行っていません`);
  });

  it("大会の件数を断定していない", () => {
    // このコンポーネントが出る条件は status=ongoing が0件（取得失敗時も空）で、
    // 他の状態の大会が無いことまでは意味しない
    expect(read(NOTICE)).not.toContain("掲載している大会はなく");
  });

  it("Open Graph の description がデモ環境と運営の開催状況を伝える", () => {
    // 検索結果とSNSカードに出る唯一のデモ告知（バナーはクライアント描画で載らない）
    const layout = read(LAYOUT);
    expect(layout).not.toContain(RETIRED);
    expect(layout).toContain(BADGE);
    expect(layout).toContain(`${OPERATOR}による大会の募集・開催は行っていません`);
  });

  it("サンプルデータの説明を DemoBanner と二重に持たない", () => {
    expect(read(BANNER_FILE)).toContain("動作確認用");
    expect(read(NOTICE)).not.toContain("機能の確認のために");
  });
});
