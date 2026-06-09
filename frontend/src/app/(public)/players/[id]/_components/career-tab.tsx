"use client";

import { Trophy, Star, Target, TrendingUp, Crosshair, Award, AlertCircle } from "lucide-react";
import { usePlayerCareer } from "@/features/career/hooks/use-career";
import { cn } from "@/lib/utils";

interface CareerTabProps {
  playerId: string;
}

export function CareerTab({ playerId }: CareerTabProps) {
  const { data: career, isLoading, isError } = usePlayerCareer(playerId);

  if (isLoading) {
    return (
      <div className="space-y-4 pt-6">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-20 animate-pulse rounded-xl bg-white/5" />)}
        </div>
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
      {/* KPIグリッド */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard icon={Trophy} color="text-brand-400" bg="bg-brand-500/10" label="総試合数" value={career.total_matches} />
        <KpiCard icon={TrendingUp} color="text-green-400" bg="bg-green-500/10" label="勝率" value={`${winRatePct}%`} highlight={career.win_rate >= 0.6} />
        <KpiCard icon={Award} color="text-yellow-400" bg="bg-yellow-500/10" label="優勝回数" value={career.championships} />
        <KpiCard icon={Star} color="text-purple-400" bg="bg-purple-500/10" label="MVP回数" value={career.mvp_count} />
      </div>

      {/* 詳細スタッツ */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h3 className="mb-4 flex items-center gap-2 text-sm font-bold text-white">
            <Crosshair className="h-4 w-4 text-brand-400" />戦績サマリー
          </h3>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            {[
              { label: "勝利", value: `${career.total_wins}`, color: "text-green-400" },
              { label: "敗北", value: `${career.total_losses}`, color: "text-red-400" },
              { label: "大会参加数", value: `${career.tournaments_played}`, color: "text-white" },
              { label: "平均ACS", value: career.avg_acs.toFixed(1), color: "text-white" },
              { label: "平均KDA", value: career.avg_kda.toFixed(2), color: career.avg_kda >= 1.5 ? "text-green-400" : "text-white" },
              { label: "K/D/A", value: `${career.avg_kills.toFixed(1)}/${career.avg_deaths.toFixed(1)}/${career.avg_assists.toFixed(1)}`, color: "text-slate-300" },
            ].map(({ label, value, color }) => (
              <div key={label} className="flex items-center justify-between border-b border-white/5 pb-2">
                <dt className="text-slate-500">{label}</dt>
                <dd className={cn("font-bold", color)}>{value}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h3 className="mb-4 flex items-center gap-2 text-sm font-bold text-white">
            <Target className="h-4 w-4 text-brand-400" />レーティング
          </h3>
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

      {/* Agent使用率 */}
      {career.agent_usage.length > 0 && (
        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h3 className="mb-4 text-sm font-bold text-white">エージェント使用率 TOP{Math.min(career.agent_usage.length, 8)}</h3>
          <div className="space-y-2">
            {career.agent_usage.slice(0, 8).map((a) => {
              const maxGames = career.agent_usage[0].games || 1;
              return (
                <div key={a.agent} className="flex items-center gap-3">
                  <span className="w-24 flex-shrink-0 truncate text-sm font-medium text-white">{a.agent}</span>
                  <div className="flex-1">
                    <div className="h-5 overflow-hidden rounded-md bg-white/5">
                      <div className="flex h-full items-center justify-end rounded-md bg-brand-500/40 px-2" style={{ width: `${(a.games / maxGames) * 100}%` }}>
                        <span className="text-[10px] text-white">{a.games}試合</span>
                      </div>
                    </div>
                  </div>
                  <span className="w-12 flex-shrink-0 text-right text-xs text-slate-400">{(a.win_rate * 100).toFixed(0)}%</span>
                  <span className="w-12 flex-shrink-0 text-right text-xs font-semibold text-brand-400">{a.avg_kda.toFixed(2)}</span>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Map勝率 */}
      {career.map_performance.length > 0 && (
        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h3 className="mb-4 text-sm font-bold text-white">マップ勝率</h3>
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
