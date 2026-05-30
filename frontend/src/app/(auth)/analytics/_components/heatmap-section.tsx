"use client";

import { Grid3X3 } from "lucide-react";
import { useAnalyticsHeatmap } from "@/features/analytics/hooks/use-analytics";
import { useAnalyticsFilterStore } from "@/store/analytics-filter-store";
import { HeatMap } from "@/features/analytics/components/heat-map";

function Skeleton() {
  return <div className="h-48 animate-pulse rounded-xl bg-white/5" />;
}

export function HeatMapSection() {
  const { game, tournamentId } = useAnalyticsFilterStore();

  const { data, isLoading } = useAnalyticsHeatmap({
    game,
    tournamentId: tournamentId || undefined,
  });

  return (
    <section className="rounded-xl border border-white/10 bg-slate-900">
      <div className="flex items-center gap-2 border-b border-white/10 px-5 py-4">
        <div className="rounded-lg bg-cyan-500/10 p-1.5">
          <Grid3X3 className="h-4 w-4 text-cyan-400" />
        </div>
        <div>
          <h2 className="text-sm font-bold text-white">MAP × Agent ヒートマップ</h2>
          <p className="text-xs text-slate-500">各MAPでのエージェント勝率分布</p>
        </div>
      </div>

      <div className="px-5 py-4">
        {isLoading && <Skeleton />}
        {!isLoading && (data?.length ?? 0) === 0 && (
          <div className="flex h-32 items-center justify-center">
            <p className="text-sm text-slate-500">ヒートマップデータがありません</p>
          </div>
        )}
        {!isLoading && (data?.length ?? 0) > 0 && (
          <HeatMap data={data!} />
        )}
      </div>
    </section>
  );
}
