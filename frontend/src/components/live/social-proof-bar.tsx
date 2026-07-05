"use client";

import { Shield, User, Trophy, Swords, Crown, Star, DoorOpen, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLive } from "@/features/live/provider/live-provider";
import { AnimatedNumber } from "./animated-number";

/** 「使われているサービス」を示す社会的証明バンド（累計＋ライブ / CountUp）。 */
export function SocialProofBar() {
  const { live, totals } = useLive();

  const items = [
    { icon: Shield, color: "text-brand-400", label: "登録チーム", value: totals?.teams ?? 0 },
    { icon: User, color: "text-cyan-400", label: "登録プレイヤー", value: totals?.players ?? 0 },
    { icon: Trophy, color: "text-yellow-400", label: "開催大会", value: totals?.tournaments ?? 0 },
    { icon: DoorOpen, color: "text-green-400", label: "受付中大会", value: live?.registration_open_tournaments ?? 0, live: true },
    { icon: Zap, color: "text-red-400", label: "開催中大会", value: live?.ongoing_tournaments ?? 0, live: true },
    { icon: Swords, color: "text-purple-400", label: "総試合数", value: totals?.matches ?? 0 },
    { icon: Crown, color: "text-amber-400", label: "優勝チーム", value: totals?.champions ?? 0 },
    { icon: Star, color: "text-pink-400", label: "MVP受賞", value: totals?.mvps ?? 0 },
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
            <p className="text-xl font-black text-white sm:text-2xl">
              <AnimatedNumber value={it.value} durationMs={1200} />
            </p>
            <p className="text-[11px] text-slate-500">{it.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
