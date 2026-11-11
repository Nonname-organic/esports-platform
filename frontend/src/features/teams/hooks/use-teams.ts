"use client";

import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { teamApi, membershipApi, type TeamCreateInput, type TeamUpdateInput, type InviteMemberInput } from "../api/team-api";

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
  invitations: (id: string) => [...teamKeys.all, "invitations", id] as const,
  myInvitations: () => [...teamKeys.all, "my-invitations"] as const,
  myMemberships: () => [...teamKeys.all, "my-memberships"] as const,
};

/** 自分のチーム一覧。公開ページで使う場合は enabled で未ログイン時の呼び出しを止める。 */
export function useMyTeams(enabled = true) {
  return useQuery({
    queryKey: teamKeys.mine(),
    queryFn: () => teamApi.mine(),
    select: (res) => res.data,
    enabled,
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

export function useInviteMember(teamId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: InviteMemberInput) => teamApi.invite(teamId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: teamKeys.invitations(teamId) }),
  });
}

/** チームの招待の一覧（オーナー・キャプテンだけが見られる） */
export function useTeamInvitations(teamId: string, enabled = true) {
  return useQuery({
    queryKey: teamKeys.invitations(teamId),
    queryFn: () => teamApi.listInvitations(teamId),
    select: (res) => res.data,
    enabled: !!teamId && enabled,
  });
}

export function useCancelInvitation(teamId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (invitationId: string) => teamApi.cancelInvitation(teamId, invitationId),
    onSuccess: () => qc.invalidateQueries({ queryKey: teamKeys.invitations(teamId) }),
  });
}

export function useMyTeamInvitations(enabled = true) {
  return useQuery({
    queryKey: teamKeys.myInvitations(),
    queryFn: () => membershipApi.myInvitations(),
    select: (res) => res.data,
    enabled,
  });
}

export function useRespondInvitation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, accept }: { id: string; accept: boolean }) => {
      if (accept) await membershipApi.accept(id);
      else await membershipApi.decline(id);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: teamKeys.all }),
  });
}

export function useMyMemberships(enabled = true) {
  return useQuery({
    queryKey: teamKeys.myMemberships(),
    queryFn: () => membershipApi.myMemberships(),
    select: (res) => res.data,
    enabled,
  });
}

export function useDecideMembership() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, confirm }: { id: string; confirm: boolean }) =>
      confirm ? membershipApi.confirm(id) : membershipApi.reject(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: teamKeys.all }),
  });
}

export function useRemoveMember(teamId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (playerId: string) => teamApi.removeMember(teamId, playerId),
    onSuccess: () => qc.invalidateQueries({ queryKey: teamKeys.members(teamId) }),
  });
}
