"use client";

import { useQuery } from "@tanstack/react-query";
import { playerProfileApi } from "../api/player-profile-api";

export function usePlayerAnalysis(id: string) {
  return useQuery({
    queryKey: ["player-profile", "analysis", id],
    queryFn: () => playerProfileApi.analysis(id),
    select: (res) => res.data,
    enabled: !!id,
    staleTime: 30 * 60 * 1000,
  });
}

export function usePlayerHistory(id: string) {
  return useQuery({
    queryKey: ["player-profile", "history", id],
    queryFn: () => playerProfileApi.history(id),
    select: (res) => res.data,
    enabled: !!id,
    staleTime: 15 * 60 * 1000,
  });
}
