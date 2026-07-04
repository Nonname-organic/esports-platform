"use client";

import { useEffect, useState } from "react";

/** epoch(ms) からの相対経過を「X秒前 / X分前」で返し、毎秒更新する。 */
export function useRelativeSeconds(epochMs: number | null): string {
  const [, force] = useState(0);
  useEffect(() => {
    const t = setInterval(() => force((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, []);
  if (!epochMs) return "—";
  const sec = Math.max(0, Math.round((Date.now() - epochMs) / 1000));
  if (sec < 60) return `${sec}秒前`;
  return `${Math.floor(sec / 60)}分前`;
}
