import { apiClient } from "@/lib/api-client";
import type {
  Team,
  TeamMember,
  TeamStats,
  TeamAnalytics,
  TeamMatchSummary,
} from "@/types/team";
import type { ApiResponse, ListResponse } from "@/types/tournament";

export const teamApi = {
  get: (id: string): Promise<ApiResponse<Team>> =>
    apiClient.get(`/api/v1/teams/${id}`),

  getStats: (id: string): Promise<ApiResponse<TeamStats>> =>
    apiClient.get(`/api/v1/teams/${id}/stats`),

  getMembers: (id: string): Promise<{ data: TeamMember[] }> =>
    apiClient.get(`/api/v1/teams/${id}/members`),

  getMatches: (
    id: string,
    params?: { limit?: number; cursor?: string; status?: string },
  ): Promise<ListResponse<TeamMatchSummary>> => {
    const qs = new URLSearchParams();
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.cursor) qs.set("cursor", params.cursor);
    if (params?.status) qs.set("status", params.status);
    const q = qs.toString();
    return apiClient.get(`/api/v1/teams/${id}/matches${q ? `?${q}` : ""}`);
  },

  getAnalytics: (id: string): Promise<ApiResponse<TeamAnalytics>> =>
    apiClient.get(`/api/v1/teams/${id}/analytics`),
};
