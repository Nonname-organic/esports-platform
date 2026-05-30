import { apiClient } from "@/lib/api-client";
import type {
  Player,
  PlayerCareerStats,
  PlayerAnalytics,
  PlayerMatchHistory,
} from "@/types/player";
import type { ApiResponse, ListResponse } from "@/types/tournament";

export const playerApi = {
  get: (id: string): Promise<ApiResponse<Player>> =>
    apiClient.get(`/api/v1/players/${id}`),

  getStats: (id: string): Promise<ApiResponse<PlayerCareerStats>> =>
    apiClient.get(`/api/v1/players/${id}/stats`),

  getAnalytics: (id: string): Promise<ApiResponse<PlayerAnalytics>> =>
    apiClient.get(`/api/v1/players/${id}/analytics`),

  getMatchHistory: (
    id: string,
    params?: { limit?: number; cursor?: string },
  ): Promise<ListResponse<PlayerMatchHistory>> => {
    const qs = new URLSearchParams();
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.cursor) qs.set("cursor", params.cursor);
    const q = qs.toString();
    return apiClient.get(`/api/v1/players/${id}/match-history${q ? `?${q}` : ""}`);
  },
};
