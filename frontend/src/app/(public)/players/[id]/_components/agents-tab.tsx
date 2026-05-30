"use client";

import { Target, AlertCircle } from "lucide-react";
import { usePlayerAnalytics } from "@/features/players/hooks/use-player";
import { AgentUsageChart } from "@/features/players/components/agent-usage-chart";

interface AgentsTabProps {
  playerId: string;
}

export function AgentsTab({ playerId }: AgentsTabProps) {
  const { data: analytics, isLoading, isError } = usePlayerAnalytics(playerId);

  if (isLoading) {
    return (
      <div className="space-y-4 pt-6">
        <div className="h-64 animate-pulse rounded-xl bg-white/5" />
        <div className="h-48 animate-pulse rounded-xl bg-white/5" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center pt-6">
        <AlertCircle className="mb-3 h-10 w-10 text-slate-700" />
        <p className="text-sm text-slate-500">エージェントデータの読み込みに失敗しました</p>
      </div>
    );
  }

  const agentUsage = analytics?.agent_usage ?? [];

  if (agentUsage.length === 0) {
    return (
      <div className="flex flex-col items-center py-24 text-center pt-6">
        <Target className="mb-4 h-12 w-12 text-slate-700" />
        <p className="font-semibold text-white">エージェントデータがありません</p>
        <p className="mt-1 text-sm text-slate-400">試合参加後にデータが表示されます</p>
      </div>
    );
  }

  // 最多使用エージェント
  const topAgent = [...agentUsage].sort((a, b) => b.games - a.games)[0];
  const bestWrAgent = [...agentUsage].sort((a, b) => b.win_rate - a.win_rate)[0];
  const bestKdaAgent = [...agentUsage].sort((a, b) => b.avg_kda - a.avg_kda)[0];

  return (
    <div className="space-y-6 pt-6">
      {/* ハイライト */}
      <div className="grid grid-cols-3 gap-3">
        <HighlightCard
          label="最多使用"
          agent={topAgent.agent}
          value={`${topAgent.games} 試合`}
          color="text-brand-400"
        />
        <HighlightCard
          label="最高勝率"
          agent={bestWrAgent.agent}
          value={`${(bestWrAgent.win_rate * 100).toFixed(1)}%`}
          color="text-green-400"
        />
        <HighlightCard
          label="最高KDA"
          agent={bestKdaAgent.agent}
          value={bestKdaAgent.avg_kda.toFixed(2)}
          color="text-purple-400"
        />
      </div>

      {/* Agent利用率チャート + テーブル */}
      <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <div className="mb-4 flex items-center gap-2">
          <div className="rounded-lg bg-brand-500/10 p-1.5">
            <Target className="h-4 w-4 text-brand-400" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">Agent利用率</h2>
            <p className="text-xs text-slate-500">{agentUsage.length} エージェント</p>
          </div>
        </div>
        <AgentUsageChart data={agentUsage} />
      </section>
    </div>
  );
}

function HighlightCard({
  label,
  agent,
  value,
  color,
}: {
  label: string;
  agent: string;
  value: string;
  color: string;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-slate-900 p-4 text-center">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-bold text-white">{agent}</p>
      <p className={`mt-0.5 text-lg font-black ${color}`}>{value}</p>
    </div>
  );
}
