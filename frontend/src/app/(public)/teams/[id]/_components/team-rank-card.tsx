"use client";

import { useTeamRankCard } from "@/features/rankings/hooks/use-rankings";
import { RankCard } from "@/components/rank-card";

/** 公開チームページの Rank Card（Achievement Card の下に配置）。 */
export function TeamRankCard({ teamId }: { teamId: string }) {
  const { data: card, isLoading } = useTeamRankCard(teamId);
  if (isLoading) return <div className="h-56 animate-pulse rounded-xl border border-white/10 bg-white/5" />;
  if (!card) return null;
  return <RankCard card={card} heading="RANK" />;
}
