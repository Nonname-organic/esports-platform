"use client";

import { useEffect, useRef, useState } from "react";
import { Zap, DoorOpen, Trophy, Shield, Swords, Coins, Crown, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLive } from "@/features/live/provider/live-provider";
import { AnimatedNumber } from "./animated-number";

/**
 * 社会的証明バンド（累計＋ライブ / CountUp）。
 * 数値は全て実データ（受付中/開催中はライブ、累計は API）。モックはしない。
 * 値更新時にタイルを Glow/Pulse/Scale で強調。
 */
export function SocialProofBar() {
  const { live, totals } = useLive();

  const items = [
    { icon: Zap, color: "text-red-400", label: "開催中大会", value: live?.ongoing_tournaments ?? 0, live: true },
    { icon: DoorOpen, color: "text-green-400", label: "受付中大会", value: live?.registration_open_tournaments ?? 0, live: true },
    { icon: Trophy, color: "text-yellow-400", label: "総大会", value: totals?.tournaments ?? 0 },
    { icon: Shield, color: "text-brand-400", label: "参加チーム", value: totals?.teams ?? 0 },
    { icon: Swords, color: "text-purple-400", label: "総試合数", value: totals?.matches ?? 0 },
    { icon: Coins, color: "text-yellow-400", label: "総賞金", value: Math.round(totals?.total_prize ?? 0), prefix: "¥" },
    { icon: Crown, color: "text-amber-400", label: "優勝チーム", value: totals?.champions ?? 0 },
    { icon: Star, color: "text-pink-400", label: "MVP受賞", value: totals?.mvps ?? 0 },
  ];

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.02] px-4 py-4">
      <div className="grid grid-cols-2 gap-x-4 gap-y-4 sm:grid-cols-4 xl:grid-cols-8">
        {items.map((it) => (
          <ProofTile key={it.label} {...it} />
        ))}
      </div>
    </div>
  );
}

function ProofTile({
  icon: Icon, color, label, value, live, prefix,
}: {
  icon: React.ElementType; color: string; label: string; value: number; live?: boolean; prefix?: string;
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
    <div className={cn("flex flex-col items-center rounded-xl px-1 py-1 text-center transition-transform", pulse && "card-pulse scale-[1.04]")}>
      <div className="mb-1 flex items-center gap-1.5">
        <Icon className={cn("h-4 w-4", color)} />
        {live && <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-live-blink" aria-hidden />}
      </div>
      <p className="text-lg font-black text-white sm:text-2xl">
        {prefix && <span className="text-slate-400">{prefix}</span>}
        <AnimatedNumber value={value} durationMs={1200} />
      </p>
      <p className="text-[11px] text-slate-500">{label}</p>
    </div>
  );
}
