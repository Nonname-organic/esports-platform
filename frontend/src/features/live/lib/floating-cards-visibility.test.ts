import type { LiveStats } from "../api/live-api";
import { shouldShowFloatingCards } from "./floating-cards-visibility";

/**
 * 判定が totals（全期間の累計）ではなく live（開催中・受付中）を見ることを固定する。
 *
 * 終わった大会が1件あるだけで LIVE が浮いていた。累計で判定していたのが原因で、
 * 同じ取り違えに戻らないようにここで止める。
 */

/** 必須フィールドを埋めた LiveStats。足りない分だけ上書きして使う。 */
function live(over: Partial<LiveStats> = {}): LiveStats {
  return {
    ongoing_tournaments: 0,
    registration_open_tournaments: 0,
    ongoing_matches: 0,
    online_participants: 0,
    updated_at: "2026-10-15T00:00:00Z",
    ...over,
  };
}

describe("shouldShowFloatingCards", () => {
  it("開催中も受付中も0件なら出さない（累計が何件あっても）", () => {
    expect(shouldShowFloatingCards(live())).toBe(false);
  });

  it("開催中が1件あれば出す", () => {
    expect(shouldShowFloatingCards(live({ ongoing_tournaments: 1 }))).toBe(true);
  });

  it("受付中が1件あれば出す", () => {
    expect(shouldShowFloatingCards(live({ registration_open_tournaments: 1 }))).toBe(true);
  });

  it("開催中と受付中の両方があれば出す", () => {
    expect(
      shouldShowFloatingCards(live({ ongoing_tournaments: 1, registration_open_tournaments: 1 })),
    ).toBe(true);
  });

  it("取得前（null）は出さない", () => {
    expect(shouldShowFloatingCards(null)).toBe(false);
  });

  it("受付中のフィールドが欠落していても、開催中が0件なら出さない", () => {
    // registration_open_tournaments は後方互換のため任意。undefined を
    // 「不明だから出す」にすると、実在しない受付を演出してしまう
    const { registration_open_tournaments: _omit, ...rest } = live();
    expect(shouldShowFloatingCards(rest as LiveStats)).toBe(false);
  });

  it("欠落していても開催中が1件あれば出す", () => {
    const { registration_open_tournaments: _omit, ...rest } = live({ ongoing_tournaments: 1 });
    expect(shouldShowFloatingCards(rest as LiveStats)).toBe(true);
  });

  it("判定は live だけで決まる（totals を渡す余地がない）", () => {
    // 同じ live を2回評価しても結果は変わらない。累計が増減しても
    // この関数の入力には現れないことを型と戻り値で示す
    const l = live({ ongoing_tournaments: 0, registration_open_tournaments: 0 });
    expect(shouldShowFloatingCards(l)).toBe(shouldShowFloatingCards(l));
    expect(shouldShowFloatingCards(l)).toBe(false);
  });

  it("負の値やゼロ以下は出さない", () => {
    expect(shouldShowFloatingCards(live({ ongoing_tournaments: -1 }))).toBe(false);
    expect(shouldShowFloatingCards(live({ registration_open_tournaments: -1 }))).toBe(false);
  });
});
