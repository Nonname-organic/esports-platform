import {
  formatDate,
  formatDateShort,
  formatTime,
  isSameDayJST,
  getMatchStatusLabel,
  getStatusLabel,
} from "./utils";

// API は日時を必ず Z 付きで返す（DB 側も全列 timestamptz）。
// ここでの期待値は「UTC の瞬間を日本時間で書いたもの」。
describe("日時のJST固定", () => {
  it("UTC の値を日本時間で出す", () => {
    // 15:47Z は JST で翌日 0:47
    expect(formatDate("2026-08-24T15:47:00Z")).toBe("2026年8月25日 00:47");
    expect(formatDateShort("2026-08-24T15:47:00Z")).toBe("8/25 0:47");
    expect(formatTime("2026-08-24T15:47:00Z")).toBe("0:47");
  });

  it("UTC のまま出していた旧挙動に戻っていない", () => {
    expect(formatDate("2026-08-24T15:47:00Z")).not.toBe("2026年8月24日 15:47");
    expect(formatDateShort("2026-08-03T15:47:00Z")).not.toBe("8/3 15:47");
  });

  it("9時間を二重に足していない（JSTの値を渡しても+18時間にならない）", () => {
    // 00:47+09:00 は 15:47Z と同じ瞬間。表記が違っても結果は一致する。
    expect(formatDate("2026-08-25T00:47:00+09:00")).toBe("2026年8月25日 00:47");
    expect(formatDate("2026-08-25T00:47:00+09:00")).toBe(formatDate("2026-08-24T15:47:00Z"));
  });

  it("日付を跨ぐ", () => {
    expect(formatDateShort("2026-08-03T15:47:00Z")).toBe("8/4 0:47");
    expect(formatDate("2026-08-03T14:59:00Z")).toBe("2026年8月3日 23:59");
  });

  it("月を跨ぐ", () => {
    expect(formatDateShort("2026-09-30T15:00:00Z")).toBe("10/1 0:00");
    expect(formatDate("2026-09-30T14:59:00Z")).toBe("2026年9月30日 23:59");
  });

  it("年を跨ぐ", () => {
    expect(formatDate("2026-12-31T15:00:00Z")).toBe("2027年1月1日 00:00");
    expect(formatDateShort("2026-12-31T15:00:00Z")).toBe("1/1 0:00");
  });

  it("深夜0時が 24:00 にならない", () => {
    expect(formatTime("2026-09-30T15:00:00Z")).toBe("0:00");
    expect(formatDate("2026-09-30T15:00:00Z")).toBe("2026年10月1日 00:00");
  });

  it("Date インスタンスでも文字列でも同じ結果になる", () => {
    const iso = "2026-08-24T15:47:00Z";
    expect(formatDate(new Date(iso))).toBe(formatDate(iso));
    expect(formatDateShort(new Date(iso))).toBe(formatDateShort(iso));
  });

  it("値が無いときは未定を返す", () => {
    expect(formatDate(null)).toBe("未定");
    expect(formatDate(undefined)).toBe("未定");
    expect(formatDate("")).toBe("未定");
    expect(formatDateShort(null)).toBe("未定");
    expect(formatTime(null)).toBe("未定");
  });
});

describe("isSameDayJST", () => {
  it("日本時間で同じ日なら true", () => {
    // どちらも JST では 8/25
    expect(isSameDayJST("2026-08-24T15:00:00Z", "2026-08-24T23:00:00Z")).toBe(true);
  });

  it("日本時間で日が変わるなら false", () => {
    // 14:00Z は JST 8/24 23:00、15:00Z は JST 8/25 0:00
    expect(isSameDayJST("2026-08-24T14:00:00Z", "2026-08-24T15:00:00Z")).toBe(false);
  });

  it("UTC では同日でも日本時間で別日なら false", () => {
    expect(isSameDayJST("2026-08-24T01:00:00Z", "2026-08-24T16:00:00Z")).toBe(false);
  });

  it("年を跨ぐ比較", () => {
    expect(isSameDayJST("2026-12-31T15:00:00Z", "2027-01-01T05:00:00Z")).toBe(true);
    expect(isSameDayJST("2026-12-31T14:00:00Z", "2026-12-31T15:00:00Z")).toBe(false);
  });
});

describe("getMatchStatusLabel", () => {
  it("使われている6種すべてを日本語にする", () => {
    expect(getMatchStatusLabel("scheduled")).toBe("予定");
    expect(getMatchStatusLabel("ongoing")).toBe("LIVE");
    expect(getMatchStatusLabel("completed")).toBe("終了");
    expect(getMatchStatusLabel("cancelled")).toBe("中止");
    expect(getMatchStatusLabel("forfeit")).toBe("没収");
    expect(getMatchStatusLabel("no_show")).toBe("不戦敗");
  });

  it("内部値がそのまま画面に出ない", () => {
    expect(getMatchStatusLabel("completed")).not.toBe("completed");
  });

  it("未知の値でも落ちず、元の文字列を返す", () => {
    expect(getMatchStatusLabel("unknown_state")).toBe("unknown_state");
    expect(() => getMatchStatusLabel("")).not.toThrow();
    expect(() => getMatchStatusLabel(null)).not.toThrow();
    expect(() => getMatchStatusLabel(undefined)).not.toThrow();
    expect(getMatchStatusLabel(null)).toBe("不明");
    expect(getMatchStatusLabel(undefined)).toBe("不明");
    expect(getMatchStatusLabel("")).toBe("不明");
  });

  it("大会ステータス用の getStatusLabel と混同していない", () => {
    // 大会側は scheduled / forfeit / no_show を持たないので変換できない
    expect(getStatusLabel("scheduled")).toBe("scheduled");
    expect(getStatusLabel("no_show")).toBe("no_show");
    // ongoing は大会では「開催中」、試合では「LIVE」
    expect(getStatusLabel("ongoing")).toBe("開催中");
    expect(getMatchStatusLabel("ongoing")).toBe("LIVE");
  });
});
