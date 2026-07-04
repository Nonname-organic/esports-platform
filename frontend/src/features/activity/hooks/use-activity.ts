"use client";

import { useQuery } from "@tanstack/react-query";
import { activityApi } from "../api/activity-api";

export function usePlayerActivity(playerId: string) {
  return useQuery({
    queryKey: ["activity", "player", playerId],
    queryFn: () => activityApi.playerActivity(playerId, { limit: 30 }),
    select: (res) => res.data,
    enabled: !!playerId,
    staleTime: 60 * 1000,
  });
}
