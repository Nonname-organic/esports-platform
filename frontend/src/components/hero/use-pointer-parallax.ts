"use client";

import { useEffect, useRef } from "react";

/**
 * Hero 用のマウス視差フック（デスクトップのみ / 空気が動く程度）。
 *
 * - `pointer: fine`（マウス環境）かつ prefers-reduced-motion でない、Save-Data でない時のみ有効。
 * - pointermove を requestAnimationFrame で 1 フレーム 1 回に間引き、
 *   CSS 変数 `--hero-mx` / `--hero-my`（-1〜1）だけを更新する（レイアウト・再描画を発生させない）。
 * - 実際の移動量は CSS 側で `calc(var(--hero-mx) * 1.5%)` 等に抑える（やりすぎ禁止）。
 *
 * スクロールイベントは一切使わない。重い JS も持たない（listener 1 本 + rAF）。
 */
export function usePointerParallax<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || typeof window === "undefined") return;

    const fine = window.matchMedia("(pointer: fine)").matches;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const conn = (navigator as unknown as { connection?: { saveData?: boolean } }).connection;
    if (!fine || reduced || conn?.saveData) return;

    let raf = 0;
    let mx = 0;
    let my = 0;

    const commit = () => {
      raf = 0;
      el.style.setProperty("--hero-mx", mx.toFixed(3));
      el.style.setProperty("--hero-my", my.toFixed(3));
    };

    const onMove = (e: PointerEvent) => {
      const w = window.innerWidth || 1;
      const h = window.innerHeight || 1;
      mx = (e.clientX / w) * 2 - 1; // -1（左）〜 1（右）
      my = (e.clientY / h) * 2 - 1; // -1（上）〜 1（下）
      if (!raf) raf = requestAnimationFrame(commit);
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);

  return ref;
}
