"use client";

import { cn } from "@/lib/utils";
import { useCountdown } from "@/features/live/hooks/use-countdown";

/**
 * DD / HH / MM / SS のカウントダウン。締切が近いほど Color/Glow/Scale/Pulse を強める。
 * - normal: 通常 / soon(<24h): 黄〜橙 + glow / critical(<1h): 赤 + pulse + scale
 */
export function Countdown({
  target,
  size = "md",
  className,
}: {
  target: string | null;
  size?: "md" | "lg";
  className?: string;
}) {
  const c = useCountdown(target);
  if (!target) return null; // 締切未設定は何も表示しない
  if (c.level === "expired") {
    return <span className="text-sm font-bold text-slate-500">受付終了</span>;
  }

  const critical = c.level === "critical";
  const soon = c.level === "soon";
  const segCls = cn(
    "tabular-nums font-black leading-none",
    size === "lg" ? "text-3xl sm:text-4xl" : "text-xl sm:text-2xl",
    critical ? "text-red-400" : soon ? "text-orange-300" : "text-white",
  );

  return (
    <div
      className={cn(
        "inline-flex items-end gap-2 rounded-xl px-1 transition-transform",
        critical && "animate-live-blink scale-[1.03]",
        className,
      )}
      style={
        critical
          ? { filter: "drop-shadow(0 0 12px rgba(239,68,68,0.6))" }
          : soon
          ? { filter: "drop-shadow(0 0 8px rgba(251,146,60,0.4))" }
          : undefined
      }
      role="timer"
      aria-label="エントリー締切までの残り時間"
    >
      <Seg v={c.days} label="DAYS" cls={segCls} />
      <Colon size={size} />
      <Seg v={c.hours} label="HRS" cls={segCls} />
      <Colon size={size} />
      <Seg v={c.minutes} label="MIN" cls={segCls} />
      <Colon size={size} />
      <Seg v={c.seconds} label="SEC" cls={segCls} />
    </div>
  );
}

function Seg({ v, label, cls }: { v: number; label: string; cls: string }) {
  return (
    <span className="flex flex-col items-center gap-0.5">
      <span className={cls}>{String(v).padStart(2, "0")}</span>
      <span className="text-[9px] font-bold tracking-widest text-slate-500">{label}</span>
    </span>
  );
}

function Colon({ size }: { size: "md" | "lg" }) {
  return (
    <span className={cn("pb-3 font-black text-slate-600", size === "lg" ? "text-2xl" : "text-lg")}>:</span>
  );
}
