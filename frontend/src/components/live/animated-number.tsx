"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { useCountUp } from "@/features/live/hooks/use-count-up";

/** CountUp + 値更新時の軽いScale/Glowフラッシュ（Status Bar / Statistics Card 共通）。 */
export function AnimatedNumber({
  value,
  durationMs = 1000,
  className,
}: {
  value: number;
  durationMs?: number;
  className?: string;
}) {
  const display = useCountUp(value, durationMs);
  const [flash, setFlash] = useState(false);
  const prev = useRef(value);

  useEffect(() => {
    if (prev.current !== value) {
      prev.current = value;
      setFlash(true);
      const t = setTimeout(() => setFlash(false), 600);
      return () => clearTimeout(t);
    }
  }, [value]);

  return (
    <span className={cn("inline-block tabular-nums", flash && "count-flash", className)}>
      {display.toLocaleString()}
    </span>
  );
}
