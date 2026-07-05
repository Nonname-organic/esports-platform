"use client";

import { usePlayerRankCard } from "@/features/rankings/hooks/use-rankings";
import { RankCard } from "@/components/rank-card";

/** プレイヤープロフィールの Rank Card（Achievement と横並び配置可）。 */
export function PlayerRankCard({ playerId }: { playerId: string }) {
  const { data: card, isLoading } = usePlayerRankCard(playerId);
  if (isLoading) return <div className="h-56 animate-pulse rounded-xl border border-white/10 bg-white/5" />;
  if (!card) return null;
  return <RankCard card={card} heading="RANK" />;
}
