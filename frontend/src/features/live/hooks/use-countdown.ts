"use client";

import { useEffect, useState } from "react";

// normal(>3d) → soon(<=3d) → urgent(<=24h) → critical(<=12h) → final(<=1h) → expired
export type CountdownLevel = "normal" | "soon" | "urgent" | "critical" | "final" | "expired";

export interface CountdownParts {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
  totalMs: number;
  level: CountdownLevel;
}

const ZERO: CountdownParts = { days: 0, hours: 0, minutes: 0, seconds: 0, totalMs: 0, level: "normal" };

function compute(target: string | null): CountdownParts {
  if (!target) return { ...ZERO, level: "expired" };
  const totalMs = new Date(target).getTime() - Date.now();
  if (Number.isNaN(totalMs) || totalMs <= 0) return { ...ZERO, level: "expired" };
  const s = Math.floor(totalMs / 1000);
  const level: CountdownLevel =
    totalMs <= 3_600_000 ? "final"        // <= 1時間
    : totalMs <= 43_200_000 ? "critical"  // <= 12時間
    : totalMs <= 86_400_000 ? "urgent"    // <= 24時間
    : totalMs <= 259_200_000 ? "soon"     // <= 3日
    : "normal";
  return {
    days: Math.floor(s / 86400),
    hours: Math.floor((s % 86400) / 3600),
    minutes: Math.floor((s % 3600) / 60),
    seconds: s % 60,
    totalMs,
    level,
  };
}

/**
 * 締切までの残りを毎秒更新。SSR/初回描画は 0 で揃え（hydration mismatch回避）、
 * マウント後に実値へ更新する。24時間以内=soon / 1時間以内=critical。
 */
export function useCountdown(target: string | null): CountdownParts {
  const [parts, setParts] = useState<CountdownParts>(ZERO);
  useEffect(() => {
    setParts(compute(target));
    const t = setInterval(() => setParts(compute(target)), 1000);
    return () => clearInterval(t);
  }, [target]);
  return parts;
}
