"use client";

import { useQuery } from "@tanstack/react-query";
import { achievementApi } from "../api/achievement-api";

export const achievementKeys = {
  teamCard: (id: string) => ["achievement", "team-card", id] as const,
};

export function useTeamAchievementCard(id: string) {
  return useQuery({
    queryKey: achievementKeys.teamCard(id),
    queryFn: () => achievementApi.teamCard(id),
    select: (res) => res.data,
    staleTime: 5 * 60 * 1000,
    enabled: !!id,
  });
}
