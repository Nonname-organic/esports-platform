"use client";

import { Trophy, TrendingUp, Award, Swords, Target, Map, AlertCircle } from "lucide-react";
import { useTeamCareer } from "@/features/career/hooks/use-career";
import { cn } from "@/lib/utils";

interface CareerTabProps {
  teamId: string;
}

export function CareerTab({ teamId }: CareerTabProps) {
  const { data: career, isLoading, isError } = useTeamCareer(teamId);

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 pt-6 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-20 animate-pulse rounded-xl bg-white/5" />)}
      </div>
    );
  }

  if (isError || !career) {
    return (
      <div className="flex h-48 flex-col items-center justify-center pt-6">
        <AlertCircle className="mb-3 h-10 w-10 text-slate-700" />
        <p className="text-sm text-slate-500">キャリアデータの読み込みに失敗しました</p>
      </div>
    );
  }

  const winRatePct = (career.win_rate * 100).toFixed(1);

  return (
    <div className="space-y-6 pt-6">
      {/* KPI */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard icon={Swords} color="text-brand-400" bg="bg-brand-500/10" label="総試合数" value={career.total_matches} />
        <KpiCard icon={TrendingUp} color="text-green-400" bg="bg-green-500/10" label="勝率" value={`${winRatePct}%`} highlight={career.win_rate >= 0.6} />
        <KpiCard icon={Trophy} color="text-yellow-400" bg="bg-yellow-500/10" label="優勝回数" value={career.championships} />
        <KpiCard icon={Award} color="text-purple-400" bg="bg-purple-500/10" label="大会参加数" value={career.tournaments_played} />
      </div>

      {/* 戦績 + レート */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h3 className="mb-4 text-sm font-bold text-white">戦績</h3>
          <div className="space-y-3">
            <div className="flex h-3 overflow-hidden rounded-full bg-red-500/30">
              <div className="bg-green-500" style={{ width: `${career.win_rate * 100}%` }} />
            </div>
            <div className="flex justify-between text-sm">
              <span className="font-bold text-green-400">{career.total_wins}勝</span>
              <span className="text-slate-500">勝率 {winRatePct}%</span>
              <span className="font-bold text-red-400">{career.total_losses}敗</span>
            </div>
          </div>
        </section>

        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h3 className="mb-4 text-sm font-bold text-white">レーティング</h3>
          <div className="grid grid-cols-2 gap-4 text-center">
            <div className="rounded-lg bg-white/3 py-4">
              <p className="text-3xl font-black text-brand-400">{career.current_rating?.toLocaleString() ?? "—"}</p>
              <p className="mt-1 text-xs text-slate-500">現在レート</p>
            </div>
            <div className="rounded-lg bg-white/3 py-4">
              <p className="text-3xl font-black text-yellow-400">{career.peak_rating?.toLocaleString() ?? "—"}</p>
              <p className="mt-1 text-xs text-slate-500">最高レート</p>
            </div>
          </div>
        </section>
      </div>

      {/* マップ分析 */}
      {career.map_performance.length > 0 && (
        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h3 className="mb-4 flex items-center gap-2 text-sm font-bold text-white">
            <Map className="h-4 w-4 text-brand-400" />マップ分析
          </h3>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {career.map_performance.map((m) => {
              const pct = Math.round(m.win_rate * 100);
              return (
                <div key={m.map_name} className="flex items-center gap-3 rounded-lg bg-white/3 px-3 py-2">
                  <span className="flex-1 text-sm font-medium text-white">{m.map_name}</span>
                  <span className="text-xs text-slate-500">{m.games}試合</span>
                  <span className={cn("text-sm font-bold", pct >= 60 ? "text-green-400" : pct >= 40 ? "text-white" : "text-red-400")}>{pct}%</span>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* エージェントトレンド */}
      {career.agent_trends.length > 0 && (
        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h3 className="mb-4 flex items-center gap-2 text-sm font-bold text-white">
            <Target className="h-4 w-4 text-brand-400" />エージェントトレンド
          </h3>
          <div className="space-y-2">
            {career.agent_trends.slice(0, 8).map((a) => {
              const maxGames = career.agent_trends[0].games || 1;
              return (
                <div key={a.agent} className="flex items-center gap-3">
                  <span className="w-24 flex-shrink-0 truncate text-sm font-medium text-white">{a.agent}</span>
                  <div className="flex-1 h-4 overflow-hidden rounded-md bg-white/5">
                    <div className="h-full rounded-md bg-brand-500/40" style={{ width: `${(a.games / maxGames) * 100}%` }} />
                  </div>
                  <span className="w-12 text-right text-xs text-slate-400">{(a.win_rate * 100).toFixed(0)}%</span>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}

function KpiCard({ icon: Icon, color, bg, label, value, highlight }: {
  icon: React.ElementType; color: string; bg: string; label: string; value: string | number; highlight?: boolean;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-slate-900 p-4">
      <div className={cn("mb-2 inline-flex rounded-lg p-2", bg)}>
        <Icon className={cn("h-4 w-4", color)} />
      </div>
      <p className={cn("text-2xl font-black", highlight ? "text-green-400" : "text-white")}>{value}</p>
      <p className="text-xs text-slate-500">{label}</p>
    </div>
  );
}
