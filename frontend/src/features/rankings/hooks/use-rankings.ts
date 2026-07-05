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

export function useSeasons() {
  return useQuery({
    queryKey: ["rankings", "seasons"],
    queryFn: () => rankingApi.seasons(),
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

export function usePlayerRankings(params: { game?: string; season?: SeasonScope; limit?: number }) {
  return useQuery({
    queryKey: ["rankings", "players", params.game ?? "all", params.season ?? "all", params.limit ?? 50],
    queryFn: () => rankingApi.players(params),
    select: (res) => res.data,
    staleTime: 5 * 60 * 1000,
  });
}

export function useTeamRankCard(teamId: string) {
  return useQuery({
    queryKey: ["rankings", "team-card", teamId],
    queryFn: () => rankingApi.teamRankCard(teamId),
    select: (res) => res.data,
    enabled: !!teamId,
    staleTime: 5 * 60 * 1000,
  });
}

export function usePlayerRankCard(playerId: string) {
  return useQuery({
    queryKey: ["rankings", "player-card", playerId],
    queryFn: () => rankingApi.playerRankCard(playerId),
    select: (res) => res.data,
    enabled: !!playerId,
    staleTime: 5 * 60 * 1000,
  });
}
