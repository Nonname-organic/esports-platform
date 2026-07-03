"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { riotApi } from "../api/riot-api";

export function useRiotProfile(playerId: string) {
  return useQuery({
    queryKey: ["riot", "profile", playerId],
    queryFn: () => riotApi.profile(playerId),
    select: (res) => res.data,
    enabled: !!playerId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useLinkRiot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ playerId, riotId }: { playerId: string; riotId: string }) =>
      riotApi.link(playerId, riotId),
    onSuccess: (_, vars) => qc.invalidateQueries({ queryKey: ["riot", "profile", vars.playerId] }),
  });
}

export function useSyncRiot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (playerId: string) => riotApi.sync(playerId),
    onSuccess: (_, playerId) => {
      qc.invalidateQueries({ queryKey: ["riot", "profile", playerId] });
      qc.invalidateQueries({ queryKey: ["career", "player", playerId] });
    },
  });
}
