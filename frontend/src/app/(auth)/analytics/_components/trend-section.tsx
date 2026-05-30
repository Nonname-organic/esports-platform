"use client";

import { TrendingUp, AlertCircle } from "lucide-react";
import { useAnalyticsTrend } from "@/features/analytics/hooks/use-analytics";
import { useAnalyticsFilterStore } from "@/store/analytics-filter-store";
import { TrendChart } from "@/features/analytics/components/trend-chart";

function Skeleton() {
  return <div className="h-72 animate-pulse rounded-xl bg-white/5" />;
}

export function TrendSection() {
  const { game, period, tournamentId, teamId } = useAnalyticsFilterStore();

  const { data, isLoading, isError } = useAnalyticsTrend({
    game,
    period,
    tournamentId: tournamentId || undefined,
    teamId: teamId || undefined,
  });

  return (
    <section className="rounded-xl border border-white/10 bg-slate-900">
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-brand-500/10 p-1.5">
            <TrendingUp className="h-4 w-4 text-brand-400" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">トレンド分析</h2>
            <p className="text-xs text-slate-500">試合数・勝率・KDAの推移</p>
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-4 rounded bg-slate-700" />試合数
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-0.5 w-4 rounded bg-brand-500" />勝率
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-0.5 w-4 rounded bg-purple-400" />KDA
          </span>
        </div>
      </div>

      <div className="px-5 py-4">
        {isLoading && <Skeleton />}
        {isError && (
          <div className="flex h-64 flex-col items-center justify-center gap-2">
            <AlertCircle className="h-8 w-8 text-slate-700" />
            <p className="text-sm text-slate-500">データの読み込みに失敗しました</p>
          </div>
        )}
        {!isLoading && !isError && (data?.length ?? 0) === 0 && (
          <div className="flex h-64 items-center justify-center">
            <p className="text-sm text-slate-500">トレンドデータがありません</p>
          </div>
        )}
        {!isLoading && !isError && (data?.length ?? 0) > 0 && (
          <TrendChart data={data!} />
        )}
      </div>
    </section>
  );
}
