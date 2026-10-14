"use client";

import { cn } from "@/lib/utils";
import { useLive } from "@/features/live/provider/live-provider";
import { shouldShowFloatingCards } from "@/features/live/lib/floating-cards-visibility";

/**
 * Hero 背景をゆっくり浮遊する半透明ラベル（世界観演出のみ / クリック不可）。
 * transform/opacity のみの GPU アニメ。reduced-motion では静止。
 *
 * ラベルは固定文字列で、データに連動しない。開催中でも受付中でもないときに
 * LIVE / ENTRY OPEN / REGISTER NOW が浮いていると、開催中の大会や
 * 受付中のエントリーがあるように読める。出す条件は
 * shouldShowFloatingCards に置いた（判定だけを単体で検証したいため）。
 */

const CARDS: { label: string; cls: string; pos: string; anim: string; delay: string }[] = [
  { label: "LIVE", cls: "border-red-500/30 text-red-300", pos: "left-[6%] top-[24%]", anim: "animate-float-a", delay: "0s" },
  { label: "ENTRY OPEN", cls: "border-green-500/30 text-green-300", pos: "right-[8%] top-[30%]", anim: "animate-float-b", delay: "1.2s" },
  { label: "FINAL", cls: "border-purple-500/30 text-purple-300", pos: "left-[12%] bottom-[24%]", anim: "animate-float-c", delay: "0.6s" },
  { label: "REGISTER NOW", cls: "border-brand-500/30 text-brand-300", pos: "right-[12%] bottom-[28%]", anim: "animate-float-a", delay: "2s" },
  { label: "COMING SOON", cls: "border-white/15 text-slate-300", pos: "left-[42%] top-[14%]", anim: "animate-float-b", delay: "1.6s" },
];

export function FloatingLiveCards() {
  const { live } = useLive();

  // 取得前（null）も出さない。0件のときに一瞬だけ見えるのを避ける。
  if (!shouldShowFloatingCards(live)) return null;

  return (
    <div className="pointer-events-none absolute inset-0 hidden overflow-hidden md:block" aria-hidden>
      {CARDS.map((c) => (
        <span
          key={c.label}
          style={{ animationDelay: c.delay }}
          className={cn(
            "absolute rounded-lg border bg-white/[0.03] px-3 py-1.5 text-[11px] font-black tracking-widest backdrop-blur-sm will-change-transform",
            c.cls,
            c.pos,
            c.anim,
          )}
        >
          {c.label}
        </span>
      ))}
    </div>
  );
}
