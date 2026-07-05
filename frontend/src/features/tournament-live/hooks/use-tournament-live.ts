"use client";

import { useQuery } from "@tanstack/react-query";
import { tournamentLiveApi } from "../api/tournament-live-api";

/**
 * 大会没入ページの Read Model フック（Polling）。
 * refetchIntervalInBackground:false により非表示タブでは自動停止（Visibility対応）。
 * 将来 WebSocket/SSE 化しても Consumer（Widget）は本フックのIFを使うだけで不変。
 */
export function useTournamentOverview(id: string) {
  return useQuery({
    queryKey: ["tournament-live", "overview", id],
    queryFn: () => tournamentLiveApi.overview(id),
    select: (res) => res.data,
    enabled: !!id,
    refetchInterval: 60000,
    refetchIntervalInBackground: false,
    staleTime: 30000,
  });
}

export function useTournamentLive(id: string, enabled = true) {
  return useQuery({
    queryKey: ["tournament-live", "live", id],
    queryFn: () => tournamentLiveApi.live(id),
    select: (res) => res.data,
    enabled: !!id && enabled,
    refetchInterval: 30000,
    refetchIntervalInBackground: false,
    staleTime: 15000,
  });
}

export function useTournamentStatistics(id: string) {
  return useQuery({
    queryKey: ["tournament-live", "statistics", id],
    queryFn: () => tournamentLiveApi.statistics(id),
    select: (res) => res.data,
    enabled: !!id,
    refetchInterval: 60000,
    refetchIntervalInBackground: false,
    staleTime: 30000,
  });
}
