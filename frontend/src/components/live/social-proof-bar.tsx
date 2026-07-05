"use client";

import { DoorOpen, Zap, Trophy, Users, Crown, Star, Swords, Coins } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLive } from "@/features/live/provider/live-provider";
import { AnimatedNumber } from "./animated-number";

/**
 * 社会的証明バンド（累計＋ライブ / CountUp）。
 * 数値は全て実データ（累計は API、受付中/開催中はライブ）。モックはしない。
 */
export function SocialProofBar() {
  const { live, totals } = useLive();

  const items = [
    { icon: DoorOpen, color: "text-green-400", label: "受付中大会", value: live?.registration_open_tournaments ?? 0, live: true },
    { icon: Zap, color: "text-red-400", label: "開催中大会", value: live?.ongoing_tournaments ?? 0, live: true },
    { icon: Trophy, color: "text-yellow-400", label: "総大会数", value: totals?.tournaments ?? 0 },
    { icon: Users, color: "text-cyan-400", label: "参加者数", value: totals?.players ?? 0 },
    { icon: Crown, color: "text-amber-400", label: "優勝チーム", value: totals?.champions ?? 0 },
    { icon: Star, color: "text-pink-400", label: "MVP数", value: totals?.mvps ?? 0 },
    { icon: Swords, color: "text-purple-400", label: "総試合数", value: totals?.matches ?? 0 },
    { icon: Coins, color: "text-yellow-400", label: "総賞金", value: Math.round(totals?.total_prize ?? 0), prefix: "¥" },
  ];

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.02] px-4 py-4">
      <div className="grid grid-cols-2 gap-x-4 gap-y-4 sm:grid-cols-4 xl:grid-cols-8">
        {items.map((it) => (
          <div key={it.label} className="flex flex-col items-center text-center">
            <div className="mb-1 flex items-center gap-1.5">
              <it.icon className={cn("h-4 w-4", it.color)} />
              {it.live && <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-live-blink" aria-hidden />}
            </div>
            <p className="text-lg font-black text-white sm:text-2xl">
              {it.prefix && <span className="text-slate-400">{it.prefix}</span>}
              <AnimatedNumber value={it.value} durationMs={1200} />
            </p>
            <p className="text-[11px] text-slate-500">{it.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
