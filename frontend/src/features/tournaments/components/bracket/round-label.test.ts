import { getRoundLabel } from "./round-label";

const SE = "single_elimination";

describe("getRoundLabel / シングルエリミネーション", () => {
  // 列の位置(1始まり)と、最終ラウンドからの距離(1=決勝)の組で渡す。
  // 16チーム=4ラウンドのとき [position, fromEnd] は (1,4)(2,3)(3,2)(4,1)。
  it("16チーム（4ラウンド）の見出しが左から順に並ぶ", () => {
    expect(getRoundLabel(1, 4, SE, "winners")).toBe("Round 1");
    expect(getRoundLabel(2, 3, SE, "winners")).toBe("準々決勝");
    expect(getRoundLabel(3, 2, SE, "winners")).toBe("準決勝");
    expect(getRoundLabel(4, 1, SE, "winners")).toBe("決勝");
  });

  it("1回戦が終端からの距離で表示されない（Round 4 への退行を防ぐ）", () => {
    expect(getRoundLabel(1, 4, SE, "winners")).not.toBe("Round 4");
  });

  it("32チーム（5ラウンド）でも先頭から数えた番号になる", () => {
    expect(getRoundLabel(1, 5, SE, "winners")).toBe("Round 1");
    expect(getRoundLabel(2, 4, SE, "winners")).toBe("Round 2");
    expect(getRoundLabel(3, 3, SE, "winners")).toBe("準々決勝");
    expect(getRoundLabel(4, 2, SE, "winners")).toBe("準決勝");
    expect(getRoundLabel(5, 1, SE, "winners")).toBe("決勝");
  });

  it("8チーム・4チーム・2チームは名前付きラウンドだけで埋まる", () => {
    expect(getRoundLabel(1, 3, SE, "winners")).toBe("準々決勝");
    expect(getRoundLabel(2, 2, SE, "winners")).toBe("準決勝");
    expect(getRoundLabel(3, 1, SE, "winners")).toBe("決勝");

    expect(getRoundLabel(1, 2, SE, "winners")).toBe("準決勝");
    expect(getRoundLabel(2, 1, SE, "winners")).toBe("決勝");

    expect(getRoundLabel(1, 1, SE, "winners")).toBe("決勝");
  });

  it("bracket_side が null（シングルエリミの旧レスポンス）でも同じ結果になる", () => {
    expect(getRoundLabel(1, 4, SE, null)).toBe("Round 1");
    expect(getRoundLabel(4, 1, SE, null)).toBe("決勝");
    expect(getRoundLabel(1, 4, SE)).toBe("Round 1");
  });
});

describe("getRoundLabel / ダブルエリミネーション", () => {
  // 8チームなら Winners は round_number 1..3、Losers は 4..7、GF は 8。
  // 勝者側・敗者側は別々に buildLayout を通るため、position はそれぞれの
  // ブラケット内での位置(1始まり)になる。
  it("勝者側は単一エリミと同じ見出しになる", () => {
    expect(getRoundLabel(1, 3, SE, "winners")).toBe("準々決勝");
    expect(getRoundLabel(2, 2, SE, "winners")).toBe("準決勝");
    expect(getRoundLabel(3, 1, SE, "winners")).toBe("決勝");
  });

  it("勝者側が4ラウンド以上（16チーム）でも先頭から数える", () => {
    expect(getRoundLabel(1, 4, SE, "winners")).toBe("Round 1");
    expect(getRoundLabel(2, 3, SE, "winners")).toBe("準々決勝");
  });

  it("敗者側は昇順に並ぶ（R1 から始まり最後が敗者決勝）", () => {
    expect(getRoundLabel(1, 4, SE, "losers")).toBe("敗者 R1");
    expect(getRoundLabel(2, 3, SE, "losers")).toBe("敗者 R2");
    expect(getRoundLabel(3, 2, SE, "losers")).toBe("敗者 R3");
    expect(getRoundLabel(4, 1, SE, "losers")).toBe("敗者決勝");
  });

  it("敗者側が降順にならない（敗者 R3 から始まる退行を防ぐ）", () => {
    expect(getRoundLabel(1, 4, SE, "losers")).not.toBe("敗者 R4");
    expect(getRoundLabel(2, 3, SE, "losers")).not.toBe("敗者 R3");
  });

  it("グランドファイナルは位置に関係なく固定の見出し", () => {
    expect(getRoundLabel(1, 1, SE, "grand_finals")).toBe("グランドファイナル");
    expect(getRoundLabel(3, 2, SE, "grand_finals")).toBe("グランドファイナル");
  });
});

describe("getRoundLabel / 総当たり", () => {
  // 呼び出し側が format を single_elimination 固定で渡すため、この分岐は
  // 現状到達しない。既存の挙動を変えていないことを記録しておく。
  it("round_robin 分岐は従来どおり終端からの距離で出す（未使用）", () => {
    expect(getRoundLabel(1, 3, "round_robin", null)).toBe("第3ラウンド");
    expect(getRoundLabel(3, 1, "round_robin", null)).toBe("第1ラウンド");
  });
});
