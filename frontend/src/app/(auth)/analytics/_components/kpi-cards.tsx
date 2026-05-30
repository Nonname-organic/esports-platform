"use client";

import { Swords, Trophy, Users, Clock, Target, TrendingUp } from "lucide-react";
import { useAnalyticsWinRate } from "@/features/analytics/hooks/use-analytics";
import { useAnalyticsFilterStore } from "@/store/analytics-filter-store";
import { cn } from "@/lib/utils";

function Skeleton() {
  return <div className="h-24 animate-pulse rounded-xl bg-white/5" />;
}

function KpiCard({
  icon: Icon,
  iconBg,
  iconColor,
  label,
  value,
  sub,
  highlight,
}: {
  icon: React.ElementType;
  iconBg: string;
  iconColor: string;
  label: string;
  value: string;
  sub?: string;
  highlight?: boolean;
}) {
  return (
    <div className={cn(
      "rounded-xl border bg-slate-900 p-4 transition-colors",
      highlight ? "border-brand-500/30" : "border-white/8 hover:border-white/15",
    )}>
      <div className="mb-2.5 flex items-center justify-between">
        <div className={cn("rounded-lg p-1.5", iconBg)}>
          <Icon className={cn("h-4 w-4", iconColor)} />
        </div>
        {highlight && (
          <span className="rounded-full bg-brand-500/10 px-2 py-0.5 text-[10px] font-semibold text-brand-400">
            KEY
          </span>
        )}
      </div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className={cn("mt-0.5 text-2xl font-black", highlight ? "text-brand-400" : "text-white")}>
        {value}
      </p>
      {sub && <p className="mt-0.5 text-[10px] text-slate-600">{sub}</p>}
    </div>
  );
}

export function KpiCards() {
  const { game, tournamentId, dateFrom, dateTo } = useAnalyticsFilterStore();
  const { data, isLoading } = useAnalyticsWinRate({
    game,
    tournamentId: tournamentId || undefined,
    dateFrom: dateFrom || undefined,
    dateTo: dateTo || undefined,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} />)}
      </div>
    );
  }

  if (!data?.overview) return null;

  const kpi = data.overview;
  const durationMin = kpi.avg_match_duration_seconds
    ? Math.round(kpi.avg_match_duration_seconds / 60)
    : null;

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
      <KpiCard
        icon={TrendingUp}
        iconBg="bg-brand-500/10"
        iconColor="text-brand-400"
        label="全体勝率"
        value={`${(kpi.overall_win_rate * 100).toFixed(1)}%`}
        highlight
      />
      <KpiCard
        icon={Swords}
        iconBg="bg-green-500/10"
        iconColor="text-green-400"
        label="総試合数"
        value={kpi.total_matches.toLocaleString()}
        sub={`${kpi.total_games.toLocaleString()} ゲーム`}
      />
      <KpiCard
        icon={Trophy}
        iconBg="bg-yellow-500/10"
        iconColor="text-yellow-400"
        label="大会数"
        value={kpi.total_tournaments.toLocaleString()}
      />
      <KpiCard
        icon={Users}
        iconBg="bg-purple-500/10"
        iconColor="text-purple-400"
        label="参加チーム"
        value={kpi.active_teams.toLocaleString()}
        sub={`${kpi.active_players.toLocaleString()} プレイヤー`}
      />
      <KpiCard
        icon={Clock}
        iconBg="bg-cyan-500/10"
        iconColor="text-cyan-400"
        label="平均試合時間"
        value={durationMin ? `${durationMin}分` : "—"}
      />
      <KpiCard
        icon={Target}
        iconBg="bg-red-500/10"
        iconColor="text-red-400"
        label="最多使用エージェント"
        value={kpi.most_played_agent ?? "—"}
        sub={kpi.most_played_map ? `人気MAP: ${kpi.most_played_map}` : undefined}
      />
    </div>
  );
}
