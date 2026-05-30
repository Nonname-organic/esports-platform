"use client";

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { teamApi } from "../api/team-api";

export const teamKeys = {
  all: ["teams"] as const,
  detail: (id: string) => [...teamKeys.all, "detail", id] as const,
  stats: (id: string) => [...teamKeys.all, "stats", id] as const,
  members: (id: string) => [...teamKeys.all, "members", id] as const,
  matches: (id: string, cursor?: string) =>
    [...teamKeys.all, "matches", id, cursor] as const,
  analytics: (id: string) => [...teamKeys.all, "analytics", id] as const,
};

export function useTeam(id: string) {
  return useQuery({
    queryKey: teamKeys.detail(id),
    queryFn: () => teamApi.get(id),
    select: (res) => res.data,
    staleTime: 5 * 60 * 1000,
  });
}

export function useTeamStats(id: string) {
  return useQuery({
    queryKey: teamKeys.stats(id),
    queryFn: () => teamApi.getStats(id),
    select: (res) => res.data,
    staleTime: 2 * 60 * 1000,
  });
}

export function useTeamMembers(id: string) {
  return useQuery({
    queryKey: teamKeys.members(id),
    queryFn: () => teamApi.getMembers(id),
    select: (res) => res.data,
    staleTime: 5 * 60 * 1000,
  });
}

export function useTeamMatches(id: string, cursor?: string) {
  return useQuery({
    queryKey: teamKeys.matches(id, cursor),
    queryFn: () => teamApi.getMatches(id, { limit: 20, cursor }),
    staleTime: 60 * 1000,
    placeholderData: keepPreviousData,
  });
}

export function useTeamAnalytics(id: string) {
  return useQuery({
    queryKey: teamKeys.analytics(id),
    queryFn: () => teamApi.getAnalytics(id),
    select: (res) => res.data,
    staleTime: 10 * 60 * 1000,
  });
}
