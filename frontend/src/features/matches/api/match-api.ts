import { apiClient } from "@/lib/api-client";
import type { MatchDetail, MatchStatus, MatchSummary } from "@/types/match";
import type { ApiResponse, ListResponse } from "@/types/tournament";

export const matchApi = {
  get: (id: string): Promise<ApiResponse<MatchDetail>> =>
    apiClient.get(`/api/v1/matches/${id}`),

  listByTournament: (
    tournamentId: string,
    params?: { status?: MatchStatus; limit?: number; cursor?: string },
  ): Promise<ListResponse<MatchSummary>> => {
    const qs = new URLSearchParams({ tournament_id: tournamentId });
    if (params?.status) qs.set("status", params.status);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.cursor) qs.set("cursor", params.cursor);
    return apiClient.get(`/api/v1/matches?${qs.toString()}`);
  },

  start: (id: string): Promise<void> =>
    apiClient.patch(`/api/v1/matches/${id}/start`),

  updateScore: (
    id: string,
    gameNumber: number,
    data: { team1_score: number; team2_score: number; duration_seconds?: number },
  ): Promise<void> =>
    apiClient.post(`/api/v1/matches/${id}/games/${gameNumber}/score`, data),

  registerResult: (
    id: string,
    data: {
      winner_id: string;
      was_forfeit?: boolean;
      game_stats?: unknown[];
    },
  ): Promise<void> => apiClient.post(`/api/v1/matches/${id}/result`, data),

  registerBanPick: (
    id: string,
    data: { team_id: string; action: "ban" | "pick"; map_id: string; order: number },
  ): Promise<void> => apiClient.post(`/api/v1/matches/${id}/banpick`, data),
};
