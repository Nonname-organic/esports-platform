"use client";

import { Target } from "lucide-react";
import { usePlayerCareer } from "@/features/career/hooks/use-career";
import { AgentCard, type AgentCardData } from "./shared/agent-card";
import { EmptyState } from "./shared/empty-state";

export function PlayerAgents({ playerId }: { playerId: string }) {
  const { data: career, isLoading } = usePlayerCareer(playerId);

  const agents: AgentCardData[] = (career?.agent_usage ?? []).map((a) => ({
    agent: a.agent, games: a.games, win_rate: a.win_rate, pick_rate: null,
    acs: null, kd: null, kda: a.avg_kda,
  }));

  return (
    <div className="space-y-5 pt-6">
      <div className="flex items-center gap-2">
        <div className="rounded-lg bg-brand-500/10 p-1.5"><Target className="h-4 w-4 text-brand-400" /></div>
        <div>
          <h2 className="text-sm font-bold text-white">Agents</h2>
          <p className="text-xs text-slate-500">大会でのエージェント別成績</p>
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-32 animate-pulse rounded-xl bg-white/5" />)}
        </div>
      ) : agents.length === 0 ? (
        <EmptyState icon={Target} title="エージェントデータがありません" desc="大会参加後に表示されます。" />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {agents.map((a) => <AgentCard key={a.agent} data={a} />)}
        </div>
      )}
    </div>
  );
}
