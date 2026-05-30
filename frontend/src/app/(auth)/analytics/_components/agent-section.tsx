"use client";

import { Target } from "lucide-react";
import { useAnalyticsAgents } from "@/features/analytics/hooks/use-analytics";
import { useAnalyticsFilterStore } from "@/store/analytics-filter-store";
import { AgentChart } from "@/features/analytics/components/agent-chart";

function Skeleton() {
  return <div className="h-72 animate-pulse rounded-xl bg-white/5" />;
}

export function AgentSection() {
  const { game, tournamentId, dateFrom, dateTo } = useAnalyticsFilterStore();

  const { data: agents, isLoading } = useAnalyticsAgents({
    game,
    tournamentId: tournamentId || undefined,
    dateFrom: dateFrom || undefined,
    dateTo: dateTo || undefined,
  });

  return (
    <section className="rounded-xl border border-white/10 bg-slate-900">
      <div className="flex items-center gap-2 border-b border-white/10 px-5 py-4">
        <div className="rounded-lg bg-purple-500/10 p-1.5">
          <Target className="h-4 w-4 text-purple-400" />
        </div>
        <div>
          <h2 className="text-sm font-bold text-white">エージェント統計</h2>
          <p className="text-xs text-slate-500">ピック率・バン率・勝率・KDA</p>
        </div>
      </div>

      <div className="px-5 py-4">
        {isLoading && <Skeleton />}
        {!isLoading && (agents?.length ?? 0) === 0 && (
          <div className="flex h-48 items-center justify-center">
            <p className="text-sm text-slate-500">エージェントデータがありません</p>
          </div>
        )}
        {!isLoading && (agents?.length ?? 0) > 0 && (
          <AgentChart data={agents!} />
        )}
      </div>
    </section>
  );
}
