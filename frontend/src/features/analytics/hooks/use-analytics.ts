"use client";

import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "../api/analytics-api";
import type { GameType } from "@/types/tournament";

export function useMapStats(game: GameType) {
  return useQuery({
    queryKey: ["analytics", "maps", game],
    queryFn: () => analyticsApi.mapStats(game),
    select: (res) => res.data,
    staleTime: 10 * 60 * 1000,
  });
}

export function useCompositions(game: GameType) {
  return useQuery({
    queryKey: ["analytics", "compositions", game],
    queryFn: () => analyticsApi.compositions(game),
    select: (res) => res.data,
    staleTime: 10 * 60 * 1000,
  });
}

export function useRankings(tournamentId: string) {
  return useQuery({
    queryKey: ["analytics", "rankings", tournamentId],
    queryFn: () => analyticsApi.rankings(tournamentId),
    select: (res) => res.data,
    enabled: !!tournamentId,
    staleTime: 60 * 1000,
  });
}
