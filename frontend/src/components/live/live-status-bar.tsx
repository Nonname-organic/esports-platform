"use client";

import { useEffect, useState } from "react";
import { Trophy, Swords, Users } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLive } from "@/features/live/provider/live-provider";
import { AnimatedNumber } from "./animated-number";
import { LiveDot } from "./live-dot";

function useRelativeSeconds(epochMs: number | null): string {
  const [, force] = useState(0);
  useEffect(() => {
    const t = setInterval(() => force((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, []);
  if (!epochMs) return "—";
  const sec = Math.max(0, Math.round((Date.now() - epochMs) / 1000));
  if (sec < 60) return `${sec}秒前`;
  const min = Math.floor(sec / 60);
  return `${min}分前`;
}

export function LiveStatusBar() {
  const { live, lastUpdated } = useLive();
  const rel = useRelativeSeconds(lastUpdated);

  return (
    <div className="mb-8 overflow-hidden rounded-2xl border border-white/10 bg-slate-900/70 backdrop-blur">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3 px-5 py-3.5">
        {/* LIVE 表示 */}
        <div className="flex items-center gap-2">
          <LiveDot />
          <span className="text-sm font-black tracking-wide text-green-400">LIVE</span>
        </div>

        <div className="hidden h-6 w-px bg-white/10 sm:block" />

        <Metric icon={Trophy} color="text-yellow-400" label="現在開催中" value={live?.ongoing_tournaments ?? 0} unit="大会" />
        <Metric icon={Swords} color="text-brand-400" label="進行中試合" value={live?.ongoing_matches ?? 0} unit="試合" />
        <Metric icon={Users} color="text-cyan-400" label="オンライン参加者" value={live?.online_participants ?? 0} unit="人" />

        {/* 最終更新（右寄せ・ゆっくり点滅） */}
        <div className="ml-auto flex items-center gap-2 text-xs text-slate-500">
          <span className="hidden sm:inline">最終更新</span>
          <span className="tabular-nums text-slate-400">{rel}</span>
          <span className="inline-flex items-center gap-1 text-green-400/80 animate-live-blink">
            <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
            <span className="text-[10px] font-bold tracking-wide">LIVE</span>
          </span>
        </div>
      </div>
    </div>
  );
}

function Metric({
  icon: Icon, color, label, value, unit,
}: {
  icon: React.ElementType; color: string; label: string; value: number; unit: string;
}) {
  return (
    <div className="flex items-center gap-2.5">
      <Icon className={cn("h-4 w-4 flex-shrink-0", color)} />
      <div className="leading-tight">
        <p className="text-[11px] text-slate-500">{label}</p>
        <p className="text-sm font-bold text-white">
          <AnimatedNumber value={value} durationMs={800} />
          <span className="ml-0.5 text-xs font-normal text-slate-400">{unit}</span>
        </p>
      </div>
    </div>
  );
}
