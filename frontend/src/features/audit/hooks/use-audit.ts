"use client";

import { useQuery } from "@tanstack/react-query";
import { auditApi } from "../api/audit-api";

export function useAdminAudit(params?: { action?: string; entity_type?: string }) {
  return useQuery({
    queryKey: ["audit", "admin", params],
    queryFn: () => auditApi.admin({ ...params, limit: 100 }),
    select: (res) => res.data,
    staleTime: 30 * 1000,
  });
}

export function useTeamAudit(teamId: string) {
  return useQuery({
    queryKey: ["audit", "team", teamId],
    queryFn: () => auditApi.team(teamId, { limit: 100 }),
    select: (res) => res.data,
    enabled: !!teamId,
    staleTime: 30 * 1000,
  });
}

export function useTournamentAudit(tournamentId: string, enabled = true) {
  return useQuery({
    queryKey: ["audit", "tournament", tournamentId],
    queryFn: () => auditApi.tournament(tournamentId, { limit: 100 }),
    select: (res) => res.data,
    enabled: enabled && !!tournamentId,
    staleTime: 30 * 1000,
  });
}
