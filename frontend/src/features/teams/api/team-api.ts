import { apiClient } from "@/lib/api-client";
import type {
  Team,
  TeamMember,
  TeamStats,
  TeamAnalytics,
  TeamMatchSummary,
  TeamInvitation,
  MyTeamInvitation,
  MyMemberships,
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
  /** 傾向分析（第2層）の公開設定。結果・ランキングは常に公開。 */
  stats_public?: boolean;
}

export interface InviteMemberInput {
  username: string;
  role?: string;
}

export const teamApi = {
  mine: (): Promise<ApiResponse<Team[]>> =>
    apiClient.get("/api/v1/teams/mine"),

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

  // RC4: メンバーは直接足さない。招待を送り、本人が承認したときだけ所属になる
  invite: (id: string, data: InviteMemberInput): Promise<ApiResponse<TeamInvitation>> =>
    apiClient.post(`/api/v1/teams/${id}/invitations`, data),

  listInvitations: (id: string): Promise<ApiResponse<(TeamInvitation & { invitee_username?: string | null })[]>> =>
    apiClient.get(`/api/v1/teams/${id}/invitations`),

  cancelInvitation: (id: string, invitationId: string): Promise<void> =>
    apiClient.delete(`/api/v1/teams/${id}/invitations/${invitationId}`),

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

/** 本人の操作（招待への返事・移行前の所属の確認と否認）。本人だけが行える */
export const membershipApi = {
  myInvitations: (): Promise<ApiResponse<MyTeamInvitation[]>> =>
    apiClient.get("/api/v1/me/team-invitations"),

  accept: (invitationId: string): Promise<ApiResponse<{ membership_id: string; team_id: string }>> =>
    apiClient.post(`/api/v1/team-invitations/${invitationId}/accept`),

  decline: (invitationId: string): Promise<void> =>
    apiClient.post(`/api/v1/team-invitations/${invitationId}/decline`),

  myMemberships: (): Promise<ApiResponse<MyMemberships>> =>
    apiClient.get("/api/v1/me/memberships"),

  confirm: (membershipId: string): Promise<ApiResponse<{ id: string; consent: string }>> =>
    apiClient.post(`/api/v1/me/memberships/${membershipId}/confirm`),

  reject: (membershipId: string): Promise<ApiResponse<{ id: string; consent: string }>> =>
    apiClient.post(`/api/v1/me/memberships/${membershipId}/reject`),
};
