"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { rosterApi, type ParticipationDispute } from "../api/roster-api";

export const rosterKeys = {
  all: ["rosters"] as const,
  roster: (tournamentId: string, registrationId: string) => [...rosterKeys.all, "roster", tournamentId, registrationId] as const,
  myInvitations: () => [...rosterKeys.all, "my-invitations"] as const,
  lineups: (matchId: string) => [...rosterKeys.all, "lineups", matchId] as const,
  substitutions: (matchId: string) => [...rosterKeys.all, "substitutions", matchId] as const,
  disputes: (status?: string) => [...rosterKeys.all, "disputes", status] as const,
};

export function useRoster(tournamentId: string, registrationId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: rosterKeys.roster(tournamentId, registrationId ?? ""),
    queryFn: () => rosterApi.get(tournamentId, registrationId!),
    select: (res) => res.data,
    enabled: !!registrationId && enabled,
  });
}

export function useRosterMutations(tournamentId: string, registrationId: string) {
  const qc = useQueryClient();
  const refresh = () => qc.invalidateQueries({ queryKey: rosterKeys.roster(tournamentId, registrationId) });
  return {
    add: useMutation({
      mutationFn: (data: { player_id: string; default_slot?: "starter" | "bench" }) =>
        rosterApi.add(tournamentId, registrationId, data),
      onSuccess: refresh,
    }),
    update: useMutation({
      mutationFn: ({ entryId, ...data }: { entryId: string; default_slot?: "starter" | "bench"; remove?: boolean; reason?: string }) =>
        rosterApi.update(tournamentId, registrationId, entryId, data),
      onSuccess: refresh,
    }),
  };
}

export function useMyRosterInvitations(enabled = true) {
  return useQuery({
    queryKey: rosterKeys.myInvitations(),
    queryFn: () => rosterApi.myInvitations(),
    select: (res) => res.data,
    enabled,
  });
}

export function useRespondRoster() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ entryId, action }: { entryId: string; action: "accept" | "decline" | "withdraw" }) =>
      rosterApi.respond(entryId, action),
    onSuccess: () => qc.invalidateQueries({ queryKey: rosterKeys.all }),
  });
}

export function useLineups(matchId: string, enabled = true) {
  return useQuery({
    queryKey: rosterKeys.lineups(matchId),
    queryFn: () => rosterApi.lineups(matchId),
    select: (res) => res.data,
    enabled: !!matchId && enabled,
  });
}

export function useSubstitutions(matchId: string, enabled = true) {
  return useQuery({
    queryKey: rosterKeys.substitutions(matchId),
    queryFn: () => rosterApi.substitutions(matchId),
    select: (res) => res.data,
    enabled: !!matchId && enabled,
  });
}

export function useDisputes(status?: ParticipationDispute["status"], enabled = true) {
  return useQuery({
    queryKey: rosterKeys.disputes(status),
    queryFn: () => rosterApi.listDisputes(status),
    select: (res) => res.data,
    enabled,
  });
}
