"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { scoutApi, type PlayerSearchParams } from "../api/scout-api";

export const scoutKeys = {
  players: (params: object) => ["scout", "players", params] as const,
  teams: (params: object) => ["scout", "teams", params] as const,
  recruitment: (params?: object) => ["scout", "recruitment", params] as const,
  recommendTeams: (id: string) => ["scout", "rec-teams", id] as const,
  recommendPlayers: (id: string) => ["scout", "rec-players", id] as const,
};

export function useScoutPlayers(params: PlayerSearchParams) {
  return useQuery({
    queryKey: scoutKeys.players(params),
    queryFn: () => scoutApi.searchPlayers(params),
    select: (res) => res.data,
    staleTime: 2 * 60 * 1000,
  });
}

export function useScoutTeams(params: { game?: string; region?: string; recruiting_only?: boolean }) {
  return useQuery({
    queryKey: scoutKeys.teams(params),
    queryFn: () => scoutApi.searchTeams(params),
    select: (res) => res.data,
    staleTime: 2 * 60 * 1000,
  });
}

export function useRecruitment(params?: { post_type?: string; game?: string }) {
  return useQuery({
    queryKey: scoutKeys.recruitment(params),
    queryFn: () => scoutApi.listRecruitment(params),
    select: (res) => res.data,
    staleTime: 60 * 1000,
  });
}

export function useCreateRecruitment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: scoutApi.createRecruitment,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scout", "recruitment"] }),
  });
}

export function useDeleteRecruitment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => scoutApi.deleteRecruitment(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scout", "recruitment"] }),
  });
}

export function useApply() {
  return useMutation({ mutationFn: scoutApi.apply });
}

export function useRecommendTeams(playerId: string) {
  return useQuery({
    queryKey: scoutKeys.recommendTeams(playerId),
    queryFn: () => scoutApi.recommendTeams(playerId),
    select: (res) => res.data,
    enabled: !!playerId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useRecommendPlayers(teamId: string) {
  return useQuery({
    queryKey: scoutKeys.recommendPlayers(teamId),
    queryFn: () => scoutApi.recommendPlayers(teamId),
    select: (res) => res.data,
    enabled: !!teamId,
    staleTime: 5 * 60 * 1000,
  });
}
