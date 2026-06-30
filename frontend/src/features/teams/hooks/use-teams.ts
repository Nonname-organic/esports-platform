"use client";

import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { teamApi, type TeamCreateInput, type TeamUpdateInput, type AddMemberInput } from "../api/team-api";

export const teamKeys = {
  all: ["teams"] as const,
  mine: () => [...teamKeys.all, "mine"] as const,
  list: (params?: object) => [...teamKeys.all, "list", params] as const,
  detail: (id: string) => [...teamKeys.all, "detail", id] as const,
  stats: (id: string) => [...teamKeys.all, "stats", id] as const,
  members: (id: string) => [...teamKeys.all, "members", id] as const,
  matches: (id: string, cursor?: string) =>
    [...teamKeys.all, "matches", id, cursor] as const,
  analytics: (id: string) => [...teamKeys.all, "analytics", id] as const,
};

export function useMyTeams() {
  return useQuery({
    queryKey: teamKeys.mine(),
    queryFn: () => teamApi.mine(),
    select: (res) => res.data,
    staleTime: 2 * 60 * 1000,
  });
}

export function useTeamList(params?: { game?: string; limit?: number }) {
  return useQuery({
    queryKey: teamKeys.list(params),
    queryFn: () => teamApi.list(params),
    staleTime: 5 * 60 * 1000,
  });
}

export function useTeam(id: string) {
  return useQuery({
    queryKey: teamKeys.detail(id),
    queryFn: () => teamApi.get(id),
    select: (res) => res.data,
    staleTime: 5 * 60 * 1000,
    enabled: !!id,
  });
}

export function useTeamStats(id: string) {
  return useQuery({
    queryKey: teamKeys.stats(id),
    queryFn: () => teamApi.getStats(id),
    select: (res) => res.data,
    staleTime: 2 * 60 * 1000,
    enabled: !!id,
  });
}

export function useTeamMembers(id: string) {
  return useQuery({
    queryKey: teamKeys.members(id),
    queryFn: () => teamApi.getMembers(id),
    select: (res) => res.data,
    staleTime: 5 * 60 * 1000,
    enabled: !!id,
  });
}

export function useTeamMatches(id: string, cursor?: string) {
  return useQuery({
    queryKey: teamKeys.matches(id, cursor),
    queryFn: () => teamApi.getMatches(id, { limit: 20, cursor }),
    staleTime: 60 * 1000,
    placeholderData: keepPreviousData,
    enabled: !!id,
  });
}

export function useTeamAnalytics(id: string) {
  return useQuery({
    queryKey: teamKeys.analytics(id),
    queryFn: () => teamApi.getAnalytics(id),
    select: (res) => res.data,
    staleTime: 10 * 60 * 1000,
    enabled: !!id,
  });
}

export function useCreateTeam() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TeamCreateInput) => teamApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: teamKeys.all }),
  });
}

export function useUpdateTeam(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TeamUpdateInput) => teamApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: teamKeys.detail(id) });
    },
  });
}

export function useDeleteTeam() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => teamApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: teamKeys.all }),
  });
}

export function useAddMember(teamId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AddMemberInput) => teamApi.addMember(teamId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: teamKeys.members(teamId) }),
  });
}

export function useRemoveMember(teamId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (playerId: string) => teamApi.removeMember(teamId, playerId),
    onSuccess: () => qc.invalidateQueries({ queryKey: teamKeys.members(teamId) }),
  });
}
