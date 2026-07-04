"use client";

import { useEffect, useRef, useState } from "react";

/**
 * 直近値 → target へ rAF でアニメーションするCountUp。
 * target が変わるたび前回値から補間するので、初回(0→N)も更新(N→M)も自然に動く。
 * prefers-reduced-motion 時は即座に確定。
 */
export function useCountUp(target: number, durationMs = 1000): number {
  const [value, setValue] = useState(0);
  const fromRef = useRef(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") { setValue(target); return; }
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce) { fromRef.current = target; setValue(target); return; }

    const from = fromRef.current;
    const start = performance.now();
    const step = (now: number) => {
      const p = Math.min((now - start) / durationMs, 1);
      const eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
      setValue(Math.round(from + (target - from) * eased));
      if (p < 1) {
        rafRef.current = requestAnimationFrame(step);
      } else {
        fromRef.current = target;
      }
    };
    rafRef.current = requestAnimationFrame(step);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [target, durationMs]);

  return value;
}
