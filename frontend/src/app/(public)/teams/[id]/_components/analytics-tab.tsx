"use client";

import { BarChart2, TrendingUp, AlertCircle } from "lucide-react";
import { useTeamAnalytics } from "@/features/teams/hooks/use-teams";
import { WinRateChart } from "@/features/teams/components/win-rate-chart";
import { MonthlyStatsChart } from "@/features/teams/components/monthly-stats-chart";

interface AnalyticsTabProps {
  teamId: string;
}

function ChartSkeleton() {
  return <div className="h-64 animate-pulse rounded-xl bg-white/5" />;
}

function ChartError({ message }: { message: string }) {
  return (
    <div className="flex h-64 flex-col items-center justify-center gap-2 rounded-xl border border-white/10 bg-slate-900">
      <AlertCircle className="h-8 w-8 text-slate-700" />
      <p className="text-sm text-slate-500">{message}</p>
    </div>
  );
}

export function AnalyticsTab({ teamId }: AnalyticsTabProps) {
  const { data: analytics, isLoading, isError } = useTeamAnalytics(teamId);

  if (isLoading) {
    return (
      <div className="space-y-6 pt-6">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="pt-6">
        <ChartError message="アナリティクスデータの読み込みに失敗しました" />
      </div>
    );
  }

  const hasWinRate = (analytics?.win_rate_history.length ?? 0) > 0;
  const hasMonthly = (analytics?.monthly_stats.length ?? 0) > 0;

  return (
    <div className="space-y-6 pt-6">
      {/* 勝率推移 */}
      <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <div className="mb-4 flex items-center gap-2">
          <div className="rounded-lg bg-brand-500/10 p-1.5">
            <TrendingUp className="h-4 w-4 text-brand-400" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">勝率推移</h2>
            <p className="text-xs text-slate-500">月別の勝率とレーティング変動</p>
          </div>
        </div>

        {hasWinRate ? (
          <WinRateChart data={analytics!.win_rate_history} />
        ) : (
          <div className="flex h-40 items-center justify-center">
            <p className="text-sm text-slate-500">データが不足しています</p>
          </div>
        )}
      </section>

      {/* 月別成績 */}
      <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <div className="mb-4 flex items-center gap-2">
          <div className="rounded-lg bg-green-500/10 p-1.5">
            <BarChart2 className="h-4 w-4 text-green-400" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">月別成績</h2>
            <p className="text-xs text-slate-500">月ごとの勝敗数</p>
          </div>
        </div>

        {hasMonthly ? (
          <MonthlyStatsChart data={analytics!.monthly_stats} />
        ) : (
          <div className="flex h-40 items-center justify-center">
            <p className="text-sm text-slate-500">データが不足しています</p>
          </div>
        )}
      </section>

      {/* サマリー統計 */}
      {analytics && hasWinRate && (
        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h2 className="mb-4 text-sm font-bold text-white">期間サマリー</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 text-center">
            {(() => {
              const history = analytics.win_rate_history;
              const latestWR = history[history.length - 1]?.win_rate ?? 0;
              const firstWR = history[0]?.win_rate ?? 0;
              const wrDelta = latestWR - firstWR;
              const totalMatches = analytics.monthly_stats.reduce(
                (acc, m) => acc + m.wins + m.losses, 0
              );
              const totalWins = analytics.monthly_stats.reduce((acc, m) => acc + m.wins, 0);
              const avgWR = totalMatches > 0 ? (totalWins / totalMatches) * 100 : 0;

              return [
                {
                  label: "期間試合数",
                  value: totalMatches.toString(),
                  sub: "総試合",
                  color: "text-white",
                },
                {
                  label: "期間勝率",
                  value: `${avgWR.toFixed(1)}%`,
                  sub: "平均",
                  color: avgWR >= 60 ? "text-green-400" : avgWR >= 40 ? "text-white" : "text-red-400",
                },
                {
                  label: "勝率変化",
                  value: `${wrDelta >= 0 ? "+" : ""}${(wrDelta * 100).toFixed(1)}%`,
                  sub: "全期間",
                  color: wrDelta >= 0 ? "text-green-400" : "text-red-400",
                },
                {
                  label: "最新レーティング",
                  value: (history[history.length - 1]?.rating ?? 0).toLocaleString(),
                  sub: "Rating",
                  color: "text-brand-400",
                },
              ].map(({ label, value, sub, color }) => (
                <div key={label} className="rounded-lg bg-white/3 px-3 py-3">
                  <p className="text-xs text-slate-500">{label}</p>
                  <p className={`mt-1 text-xl font-black ${color}`}>{value}</p>
                  <p className="text-[10px] text-slate-600">{sub}</p>
                </div>
              ));
            })()}
          </div>
        </section>
      )}
    </div>
  );
}
