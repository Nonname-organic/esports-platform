"use client";

import { Trophy, Shield, User, Swords } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLive } from "@/features/live/provider/live-provider";
import { AnimatedNumber } from "./animated-number";

/** プラットフォーム累計（API取得時に 0→N の CountUp、更新時に軽くScale/Glow）。 */
export function StatisticsCard() {
  const { totals } = useLive();

  const tiles = [
    { icon: Trophy, color: "text-yellow-400", bg: "bg-yellow-500/10", label: "開催大会数", value: totals?.tournaments ?? 0 },
    { icon: Shield, color: "text-brand-400", bg: "bg-brand-500/10", label: "登録チーム", value: totals?.teams ?? 0 },
    { icon: User, color: "text-cyan-400", bg: "bg-cyan-500/10", label: "登録プレイヤー", value: totals?.players ?? 0 },
    { icon: Swords, color: "text-purple-400", bg: "bg-purple-500/10", label: "総試合数", value: totals?.matches ?? 0 },
  ];

  return (
    <div className="mb-12 grid grid-cols-2 gap-4 lg:grid-cols-4">
      {tiles.map((t) => (
        <div
          key={t.label}
          className="rounded-2xl border border-white/10 bg-slate-900 p-5 transition-colors hover:border-white/20"
        >
          <div className={cn("mb-3 inline-flex rounded-xl p-2.5", t.bg)}>
            <t.icon className={cn("h-5 w-5", t.color)} />
          </div>
          <p className="text-3xl font-black text-white sm:text-4xl">
            <AnimatedNumber value={t.value} durationMs={1100} />
          </p>
          <p className="mt-1 text-sm text-slate-500">{t.label}</p>
        </div>
      ))}
    </div>
  );
}
