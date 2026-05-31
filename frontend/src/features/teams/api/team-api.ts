import { apiClient } from "@/lib/api-client";
import type {
  Team,
  TeamMember,
  TeamStats,
  TeamAnalytics,
  TeamMatchSummary,
} from "@/types/team";
import type { ApiResponse, ListResponse } from "@/types/tournament";

export interface TeamCreateInput {
  name: string;
  tag: string;
  game: string;
  description?: string;
  country?: string;
  logo_url?: string;
  banner_url?: string;
  twitter_handle?: string;
}

export interface TeamUpdateInput {
  name?: string;
  tag?: string;
  description?: string;
  country?: string;
  logo_url?: string;
  banner_url?: string;
  twitter_handle?: string;
}

export interface AddMemberInput {
  username: string;
  role?: string;
  jersey_number?: number;
}

export const teamApi = {
  list: (params?: { game?: string; limit?: number; cursor?: string }): Promise<ListResponse<Team>> => {
    const qs = new URLSearchParams();
    if (params?.game) qs.set("game", params.game);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.cursor) qs.set("cursor", params.cursor);
    const q = qs.toString();
    return apiClient.get(`/api/v1/teams${q ? `?${q}` : ""}`);
  },

  get: (id: string): Promise<ApiResponse<Team>> =>
    apiClient.get(`/api/v1/teams/${id}`),

  create: (data: TeamCreateInput): Promise<ApiResponse<Team>> =>
    apiClient.post("/api/v1/teams", data),

  update: (id: string, data: TeamUpdateInput): Promise<ApiResponse<Team>> =>
    apiClient.patch(`/api/v1/teams/${id}`, data),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/api/v1/teams/${id}`),

  getStats: (id: string): Promise<ApiResponse<TeamStats>> =>
    apiClient.get(`/api/v1/teams/${id}/stats`),

  getMembers: (id: string): Promise<ApiResponse<TeamMember[]>> =>
    apiClient.get(`/api/v1/teams/${id}/members`),

  addMember: (id: string, data: AddMemberInput): Promise<ApiResponse<TeamMember>> =>
    apiClient.post(`/api/v1/teams/${id}/members`, data),

  removeMember: (teamId: string, playerId: string): Promise<void> =>
    apiClient.delete(`/api/v1/teams/${teamId}/members/${playerId}`),

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
