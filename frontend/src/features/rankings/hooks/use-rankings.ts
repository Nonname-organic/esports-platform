"use client";

import { useQuery } from "@tanstack/react-query";
import { rankingApi, type SeasonScope } from "../api/ranking-api";

export function useTiers() {
  return useQuery({
    queryKey: ["rankings", "tiers"],
    queryFn: () => rankingApi.tiers(),
    select: (res) => res.data,
    staleTime: 60 * 60 * 1000,
  });
}

export function useGlobalRankings(params: { game?: string; season?: SeasonScope; limit?: number }) {
  return useQuery({
    queryKey: ["rankings", "global", params.game ?? "all", params.season ?? "all", params.limit ?? 50],
    queryFn: () => rankingApi.global(params),
    select: (res) => res.data,
    staleTime: 5 * 60 * 1000,
  });
}

export function useTeamRankCard(teamId: string, season: SeasonScope = "all") {
  return useQuery({
    queryKey: ["rankings", "team-card", teamId, season],
    queryFn: () => rankingApi.teamCard(teamId, season),
    select: (res) => res.data,
    enabled: !!teamId,
    staleTime: 5 * 60 * 1000,
  });
}
