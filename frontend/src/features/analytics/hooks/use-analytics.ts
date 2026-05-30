"use client";

import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "../api/analytics-api";
import type { GameType } from "@/types/tournament";
import type { AnalyticsPeriod } from "@/types/analytics";

// ── クエリキー ───────────────────────────────────────────────────────────────
export const analyticsKeys = {
  all: ["analytics"] as const,
  mapStats: (game: GameType) => [...analyticsKeys.all, "maps", game] as const,
  compositions: (game: GameType) => [...analyticsKeys.all, "compositions", game] as const,
  rankings: (tournamentId: string) => [...analyticsKeys.all, "rankings", tournamentId] as const,
  winRate: (params: object) => [...analyticsKeys.all, "winrate", params] as const,
  trend: (params: object) => [...analyticsKeys.all, "trend", params] as const,
  agents: (params: object) => [...analyticsKeys.all, "agents", params] as const,
  playerRankings: (params: object) => [...analyticsKeys.all, "players", params] as const,
  heatmap: (params: object) => [...analyticsKeys.all, "heatmap", params] as const,
};

// ── 既存フック ───────────────────────────────────────────────────────────────
export function useMapStats(game: GameType) {
  return useQuery({
    queryKey: analyticsKeys.mapStats(game),
    queryFn: () => analyticsApi.mapStats(game),
    select: (res) => res.data,
    staleTime: 10 * 60 * 1000,
  });
}

export function useCompositions(game: GameType) {
  return useQuery({
    queryKey: analyticsKeys.compositions(game),
    queryFn: () => analyticsApi.compositions(game),
    select: (res) => res.data,
    staleTime: 10 * 60 * 1000,
  });
}

export function useRankings(tournamentId: string) {
  return useQuery({
    queryKey: analyticsKeys.rankings(tournamentId),
    queryFn: () => analyticsApi.rankings(tournamentId),
    select: (res) => res.data,
    enabled: !!tournamentId,
    staleTime: 60 * 1000,
  });
}

// ── 新規フック ───────────────────────────────────────────────────────────────
export function useAnalyticsWinRate(params: {
  game: GameType;
  tournamentId?: string;
  dateFrom?: string;
  dateTo?: string;
  teamId?: string;
}) {
  return useQuery({
    queryKey: analyticsKeys.winRate(params),
    queryFn: () => analyticsApi.winRate(params),
    select: (res) => res.data,
    staleTime: 5 * 60 * 1000,
  });
}

export function useAnalyticsTrend(params: {
  game: GameType;
  period: AnalyticsPeriod;
  tournamentId?: string;
  teamId?: string;
}) {
  return useQuery({
    queryKey: analyticsKeys.trend(params),
    queryFn: () => analyticsApi.trend(params),
    select: (res) => res.data,
    staleTime: 5 * 60 * 1000,
  });
}

export function useAnalyticsAgents(params: {
  game: GameType;
  tournamentId?: string;
  dateFrom?: string;
  dateTo?: string;
}) {
  return useQuery({
    queryKey: analyticsKeys.agents(params),
    queryFn: () => analyticsApi.agents(params),
    select: (res) => res.data,
    staleTime: 10 * 60 * 1000,
  });
}

export function usePlayerRankings(params: {
  game: GameType;
  tournamentId?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: analyticsKeys.playerRankings(params),
    queryFn: () => analyticsApi.playerRankings(params),
    select: (res) => res.data,
    staleTime: 2 * 60 * 1000,
  });
}

export function useAnalyticsHeatmap(params: {
  game: GameType;
  tournamentId?: string;
}) {
  return useQuery({
    queryKey: analyticsKeys.heatmap(params),
    queryFn: () => analyticsApi.heatmap(params),
    select: (res) => res.data,
    staleTime: 10 * 60 * 1000,
  });
}
