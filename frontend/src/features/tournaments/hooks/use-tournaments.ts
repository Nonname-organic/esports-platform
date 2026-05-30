"use client";

import { useQuery, useMutation, useQueryClient, useInfiniteQuery, keepPreviousData } from "@tanstack/react-query";
import { tournamentApi } from "../api/tournament-api";
import type { TournamentListParams } from "../api/tournament-api";
import type { GameType, TournamentStatus } from "@/types/tournament";

export const tournamentKeys = {
  all: ["tournaments"] as const,
  lists: () => [...tournamentKeys.all, "list"] as const,
  list: (filters: { game?: GameType; status?: TournamentStatus }) =>
    [...tournamentKeys.lists(), filters] as const,
  detail: (id: string) => [...tournamentKeys.all, "detail", id] as const,
  bracket: (id: string) => [...tournamentKeys.all, "bracket", id] as const,
};

export function useTournaments(filters?: { game?: GameType; status?: TournamentStatus }) {
  return useInfiniteQuery({
    queryKey: tournamentKeys.list(filters ?? {}),
    queryFn: ({ pageParam }) =>
      tournamentApi.list({
        ...filters,
        cursor: pageParam as string | undefined,
        limit: 20,
      }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) =>
      lastPage.meta.has_next ? (lastPage.meta.cursor ?? undefined) : undefined,
    staleTime: 5 * 60 * 1000, // ISR 5分相当
  });
}

export function useTournament(id: string) {
  return useQuery({
    queryKey: tournamentKeys.detail(id),
    queryFn: () => tournamentApi.get(id),
    select: (res) => res.data,
    staleTime: 60 * 1000, // 1分
  });
}

export function useBracket(id: string) {
  return useQuery({
    queryKey: tournamentKeys.bracket(id),
    queryFn: () => tournamentApi.getBracket(id),
    select: (res) => res.data,
    refetchInterval: 30 * 1000, // 30秒ごとにポーリング（WS補完）
  });
}

export function useTournamentList(params: TournamentListParams & { cursor?: string }) {
  return useQuery({
    queryKey: [...tournamentKeys.all, "page", params],
    queryFn: () => tournamentApi.list({ ...params, limit: 12 }),
    staleTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  });
}

export function useCreateTournament() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: tournamentApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: tournamentKeys.lists() });
    },
  });
}

export function useRegisterTeam(tournamentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ teamId, notes }: { teamId: string; notes?: string }) =>
      tournamentApi.register(tournamentId, teamId, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: tournamentKeys.detail(tournamentId) });
    },
  });
}

export function useGenerateBracket(tournamentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => tournamentApi.generateBracket(tournamentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: tournamentKeys.bracket(tournamentId) });
    },
  });
}
