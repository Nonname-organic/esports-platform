import type { LiveStats } from "../api/live-api";

/**
 * Hero 背景の浮遊ラベルを出すかどうか。
 *
 * ラベルは LIVE / ENTRY OPEN / REGISTER NOW といった固定文字列で、
 * データには連動しない。開催中でも受付中でもないときに浮いていると、
 * 開催中の大会や受付中のエントリーがあるように読める。
 *
 * 判定に totals.tournaments（全期間の累計）を使わないのは、終わった大会や
 * 下書きが1件あるだけで「開催中」を示唆してしまうため。見るのは live 側の
 * 開催中・受付中の件数だけにする。
 *
 * registration_open_tournaments は後方互換のため任意フィールドなので、
 * 欠落は 0 として扱う。「不明だから出す」にすると、実在しない開催を
 * 演出することになる。
 */
export function shouldShowFloatingCards(live: LiveStats | null): boolean {
  if (!live) return false;
  return live.ongoing_tournaments > 0 || (live.registration_open_tournaments ?? 0) > 0;
}
