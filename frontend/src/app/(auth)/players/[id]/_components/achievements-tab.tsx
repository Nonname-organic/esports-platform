"use client";

import { Trophy, Award, Star, Crosshair, Medal, AlertCircle } from "lucide-react";
import { formatDate } from "@/lib/utils";
import { usePlayerAchievements } from "@/features/career/hooks/use-career";

interface AchievementsTabProps {
  playerId: string;
}

const ACHIEVEMENT_ICON: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  champion: { icon: Trophy, color: "text-yellow-400", bg: "bg-yellow-500/10" },
  runner_up: { icon: Medal, color: "text-slate-300", bg: "bg-slate-500/10" },
  mvp: { icon: Star, color: "text-purple-400", bg: "bg-purple-500/10" },
  top_fragger: { icon: Crosshair, color: "text-red-400", bg: "bg-red-500/10" },
  default: { icon: Award, color: "text-brand-400", bg: "bg-brand-500/10" },
};

export function AchievementsTab({ playerId }: AchievementsTabProps) {
  const { data: achievements, isLoading, isError } = usePlayerAchievements(playerId);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-3 pt-6 sm:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-24 animate-pulse rounded-xl bg-white/5" />)}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-48 flex-col items-center justify-center pt-6">
        <AlertCircle className="mb-3 h-10 w-10 text-slate-700" />
        <p className="text-sm text-slate-500">実績の読み込みに失敗しました</p>
      </div>
    );
  }

  if (!achievements || achievements.length === 0) {
    return (
      <div className="flex flex-col items-center py-24 text-center pt-6">
        <Trophy className="mb-4 h-12 w-12 text-slate-700" />
        <p className="font-semibold text-white">まだ実績がありません</p>
        <p className="mt-1 text-sm text-slate-400">大会で活躍すると実績が記録されます</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-3 pt-6 sm:grid-cols-2">
      {achievements.map((a) => {
        const cfg = ACHIEVEMENT_ICON[a.type] ?? ACHIEVEMENT_ICON.default;
        const Icon = cfg.icon;
        return (
          <div key={a.id} className="flex items-start gap-4 rounded-xl border border-white/10 bg-slate-900 p-4">
            <div className={`flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl ${cfg.bg}`}>
              <Icon className={`h-6 w-6 ${cfg.color}`} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-bold text-white">{a.title}</p>
              {a.description && <p className="mt-0.5 text-xs text-slate-400">{a.description}</p>}
              <p className="mt-1 text-[10px] text-slate-600">{a.earned_at ? formatDate(a.earned_at) : ""}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
