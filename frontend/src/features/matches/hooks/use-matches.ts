"use client";

import { useQuery } from "@tanstack/react-query";
import { matchApi } from "../api/match-api";

export const matchKeys = {
  all: ["matches"] as const,
  tournament: (id: string) => [...matchKeys.all, "tournament", id] as const,
  detail: (id: string) => [...matchKeys.all, "detail", id] as const,
};

export function useTournamentMatches(tournamentId: string) {
  return useQuery({
    queryKey: matchKeys.tournament(tournamentId),
    queryFn: () => matchApi.listByTournament(tournamentId, { limit: 100 }),
    select: (res) => res.data,
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });
}

export function useMatch(id: string) {
  return useQuery({
    queryKey: matchKeys.detail(id),
    queryFn: () => matchApi.get(id),
    select: (res) => res.data,
    staleTime: 30 * 1000,
  });
}
