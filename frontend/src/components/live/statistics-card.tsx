"use client";

import { useEffect, useRef, useState } from "react";
import { Trophy, DoorOpen, Zap, Shield, User, Swords } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLive } from "@/features/live/provider/live-provider";
import { AnimatedNumber } from "./animated-number";

/** プラットフォーム累計＋ライブ内訳。CountUp + 値更新時に軽くPulse。 */
export function StatisticsCard() {
  const { live, totals } = useLive();

  const tiles = [
    { icon: Trophy, color: "text-yellow-400", bg: "bg-yellow-500/10", label: "登録大会数", value: totals?.tournaments ?? 0 },
    { icon: DoorOpen, color: "text-green-400", bg: "bg-green-500/10", label: "受付中大会", value: live?.registration_open_tournaments ?? 0, live: true },
    { icon: Zap, color: "text-red-400", bg: "bg-red-500/10", label: "開催中大会", value: live?.ongoing_tournaments ?? 0, live: true },
    { icon: Shield, color: "text-brand-400", bg: "bg-brand-500/10", label: "登録チーム", value: totals?.teams ?? 0 },
    { icon: User, color: "text-cyan-400", bg: "bg-cyan-500/10", label: "登録プレイヤー", value: totals?.players ?? 0 },
    { icon: Swords, color: "text-purple-400", bg: "bg-purple-500/10", label: "総試合数", value: totals?.matches ?? 0 },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {tiles.map((t) => (
        <StatTile key={t.label} {...t} />
      ))}
    </div>
  );
}

function StatTile({
  icon: Icon, color, bg, label, value, live,
}: {
  icon: React.ElementType; color: string; bg: string; label: string; value: number; live?: boolean;
}) {
  const [pulse, setPulse] = useState(false);
  const prev = useRef(value);

  useEffect(() => {
    if (prev.current !== value) {
      prev.current = value;
      setPulse(true);
      const t = setTimeout(() => setPulse(false), 900);
      return () => clearTimeout(t);
    }
  }, [value]);

  return (
    <div
      className={cn(
        "rounded-2xl border border-white/10 bg-slate-900 p-4 transition-colors hover:border-white/20",
        pulse && "card-pulse",
      )}
    >
      <div className="mb-2 flex items-center justify-between">
        <div className={cn("inline-flex rounded-xl p-2", bg)}>
          <Icon className={cn("h-4 w-4", color)} />
        </div>
        {live && <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-live-blink" aria-hidden />}
      </div>
      <p className="text-2xl font-black text-white sm:text-3xl">
        <AnimatedNumber value={value} durationMs={1100} />
      </p>
      <p className="mt-0.5 text-xs text-slate-500">{label}</p>
    </div>
  );
}
