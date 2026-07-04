"use client";

import { useTeamAchievementCard } from "@/features/achievements/hooks/use-achievement-card";
import { AchievementCard } from "@/components/achievement-card";

/** 公開チームページの実績カード（DTOを取得し共通 AchievementCard へ受け渡す）。 */
export function TeamAchievements({ teamId }: { teamId: string }) {
  const { data: card, isLoading } = useTeamAchievementCard(teamId);

  if (isLoading) {
    return <div className="h-40 animate-pulse rounded-xl border border-white/10 bg-white/5" />;
  }
  if (!card) return null;

  return (
    <AchievementCard
      heading="Achievements"
      championships={card.championships}
      runnerUps={card.runner_ups}
      top4={card.top4}
      winRate={card.win_rate}
      wins={card.wins}
      losses={card.losses}
      matches={card.matches}
      tournaments={card.tournaments}
      mvps={card.mvps}
      since={card.founded_at}
      recentTitles={card.recent_titles.map((t) => ({
        placement: t.placement,
        label: t.tournament_name,
        href: `/tournaments/${t.tournament_id}`,
        date: t.ended_at,
      }))}
    />
  );
}
