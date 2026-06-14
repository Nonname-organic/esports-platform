"use client";

import { TrendingUp, BarChart2, AlertCircle } from "lucide-react";
import { usePlayerAnalytics } from "@/features/players/hooks/use-player";
import { KdaTrendChart } from "@/features/players/components/kda-trend-chart";
import { PlayerWinRateChart } from "@/features/players/components/player-win-rate-chart";

interface TrendTabProps {
  playerId: string;
}

function ChartSkeleton() {
  return <div className="h-72 animate-pulse rounded-xl bg-white/5" />;
}

function ChartError({ msg }: { msg: string }) {
  return (
    <div className="flex h-64 flex-col items-center justify-center gap-2 rounded-xl border border-white/10 bg-slate-900">
      <AlertCircle className="h-8 w-8 text-slate-700" />
      <p className="text-sm text-slate-500">{msg}</p>
    </div>
  );
}

export function TrendTab({ playerId }: TrendTabProps) {
  const { data: analytics, isLoading, isError } = usePlayerAnalytics(playerId);

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
        <ChartError msg="トレンドデータの読み込みに失敗しました" />
      </div>
    );
  }

  const hasKda = (analytics?.kda_history.length ?? 0) > 0;
  const hasWr = (analytics?.win_rate_history.length ?? 0) > 0;

  const noData = !hasKda && !hasWr;

  return (
    <div className="space-y-6 pt-6">
      {noData && (
        <div className="flex h-48 flex-col items-center justify-center rounded-xl border border-white/10 bg-slate-900">
          <TrendingUp className="mb-3 h-10 w-10 text-slate-700" />
          <p className="text-sm text-slate-500">トレンドデータはまだありません</p>
        </div>
      )}

      {/* KDA推移 */}
      {hasKda && (
        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <div className="mb-4 flex items-center gap-2">
            <div className="rounded-lg bg-green-500/10 p-1.5">
              <BarChart2 className="h-4 w-4 text-green-400" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white">KDA推移</h2>
              <p className="text-xs text-slate-500">月別 Kill/Death/Assist とKDAレシオ</p>
            </div>
          </div>
          <KdaTrendChart data={analytics!.kda_history} />

          {/* 凡例の補足 */}
          <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
            <span><span className="inline-block h-2 w-4 rounded bg-green-500 mr-1" />Kill</span>
            <span><span className="inline-block h-2 w-4 rounded bg-red-500 mr-1" />Death</span>
            <span><span className="inline-block h-2 w-4 rounded bg-yellow-500 mr-1" />Assist</span>
            <span><span className="inline-block h-2 w-4 rounded bg-purple-400 mr-1" />KDA（右軸）</span>
          </div>
        </section>
      )}

      {/* 勝率推移 */}
      {hasWr && (
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
          <PlayerWinRateChart data={analytics!.win_rate_history} />
        </section>
      )}

      {/* 期間サマリー */}
      {hasKda && analytics && (
        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h2 className="mb-4 text-sm font-bold text-white">期間サマリー</h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-center">
            {(() => {
              const kda = analytics.kda_history;
              const wr = analytics.win_rate_history;
              const avgKda =
                kda.length > 0
                  ? kda.reduce((s, d) => s + d.avg_kda, 0) / kda.length
                  : 0;
              const latestRating = wr[wr.length - 1]?.rating ?? 0;
              const totalMatches = kda.reduce((s, d) => s + d.matches, 0);
              const avgWr =
                wr.length > 0
                  ? wr.reduce((s, d) => s + d.win_rate, 0) / wr.length
                  : 0;

              return [
                { label: "期間試合数", value: totalMatches.toString(), color: "text-white" },
                { label: "平均KDA", value: avgKda.toFixed(2), color: "text-purple-400" },
                { label: "平均勝率", value: `${(avgWr * 100).toFixed(1)}%`, color: avgWr >= 0.5 ? "text-green-400" : "text-red-400" },
                { label: "最新Rating", value: latestRating.toLocaleString(), color: "text-brand-400" },
              ].map(({ label, value, color }) => (
                <div key={label} className="rounded-lg bg-white/3 px-3 py-3">
                  <p className="text-xs text-slate-500">{label}</p>
                  <p className={`mt-1 text-xl font-black ${color}`}>{value}</p>
                </div>
              ));
            })()}
          </div>
        </section>
      )}
    </div>
  );
}
