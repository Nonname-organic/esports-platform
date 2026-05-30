"use client";

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { playerApi } from "../api/player-api";

export const playerKeys = {
  all: ["players"] as const,
  detail: (id: string) => [...playerKeys.all, "detail", id] as const,
  stats: (id: string) => [...playerKeys.all, "stats", id] as const,
  analytics: (id: string) => [...playerKeys.all, "analytics", id] as const,
  history: (id: string, cursor?: string) =>
    [...playerKeys.all, "history", id, cursor] as const,
};

export function usePlayer(id: string) {
  return useQuery({
    queryKey: playerKeys.detail(id),
    queryFn: () => playerApi.get(id),
    select: (res) => res.data,
    staleTime: 5 * 60 * 1000,
  });
}

export function usePlayerStats(id: string) {
  return useQuery({
    queryKey: playerKeys.stats(id),
    queryFn: () => playerApi.getStats(id),
    select: (res) => res.data,
    staleTime: 2 * 60 * 1000,
  });
}

export function usePlayerAnalytics(id: string) {
  return useQuery({
    queryKey: playerKeys.analytics(id),
    queryFn: () => playerApi.getAnalytics(id),
    select: (res) => res.data,
    staleTime: 10 * 60 * 1000,
  });
}

export function usePlayerMatchHistory(id: string, cursor?: string) {
  return useQuery({
    queryKey: playerKeys.history(id, cursor),
    queryFn: () => playerApi.getMatchHistory(id, { limit: 20, cursor }),
    staleTime: 60 * 1000,
    placeholderData: keepPreviousData,
  });
}
