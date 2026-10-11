import type { BracketSide } from "@/types/tournament";

/**
 * ブラケットのラウンド見出し。
 *
 * 引数を2つに分けているのは、ラベルごとに必要な数え方が違うため。
 *
 *   position … 描画している列の位置（左から1始まり）
 *   fromEnd  … そのブラケットの最終ラウンドからの距離（1 = 最終ラウンド）
 *
 * 決勝・準決勝・準々決勝は終端から数えないと参加チーム数が変わるたびに
 * 意味がずれるので fromEnd を使う。逆に「Round N」「敗者 RN」は先頭から
 * 数えた番号なので position を使う。
 *
 * 以前はどちらも fromEnd で出していたため、16チームのシングルエリミで
 * 1回戦が「Round 4」になり、敗者側は「敗者 R3 → 敗者 R2 → 敗者決勝」と
 * 逆順になっていた。
 *
 * position を API の round_number ではなく描画位置から取るのは、敗者側の
 * round_number が勝者側からの通し番号（8チームなら 4〜7）になっており、
 * そのまま出すと「敗者 R4」から始まってしまうため。
 */
export function getRoundLabel(
  position: number,
  fromEnd: number,
  format: string,
  side?: BracketSide | null,
): string {
  // 呼び出し側が format を "single_elimination" 固定で渡しているため、
  // この分岐には現状到達しない。総当たりは全試合が round_number=1 で
  // 生成されるという別の課題があり、そこを直さずにラベルだけ変えても
  // 意味がないので、既存の挙動のまま残す。
  if (format === "round_robin") return `第${fromEnd}ラウンド`;
  if (side === "losers") {
    if (fromEnd === 1) return "敗者決勝";
    return `敗者 R${position}`;
  }
  if (side === "grand_finals") return "グランドファイナル";
  if (fromEnd === 1) return "決勝";
  if (fromEnd === 2) return "準決勝";
  if (fromEnd === 3) return "準々決勝";
  return `Round ${position}`;
}
