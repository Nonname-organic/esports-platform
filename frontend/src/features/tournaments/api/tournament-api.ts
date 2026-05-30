import { apiClient } from "@/lib/api-client";
import type {
  ApiResponse,
  BracketResponse,
  ListResponse,
  TournamentDetail,
  TournamentSummary,
  GameType,
  TournamentStatus,
} from "@/types/tournament";

export type TournamentSortOrder = "start_at_asc" | "start_at_desc" | "created_at_desc";

export interface TournamentListParams {
  q?: string;
  game?: GameType;
  status?: TournamentStatus;
  sort?: TournamentSortOrder;
  cursor?: string;
  limit?: number;
}

export const tournamentApi = {
  list: (params?: TournamentListParams): Promise<ListResponse<TournamentSummary>> => {
    const qs = new URLSearchParams();
    if (params?.q) qs.set("q", params.q);
    if (params?.game) qs.set("game", params.game);
    if (params?.status) qs.set("status", params.status);
    if (params?.sort) qs.set("sort", params.sort);
    if (params?.cursor) qs.set("cursor", params.cursor);
    if (params?.limit) qs.set("limit", String(params.limit));
    const query = qs.toString() ? `?${qs.toString()}` : "";
    return apiClient.get(`/api/v1/tournaments${query}`);
  },

  get: (id: string): Promise<ApiResponse<TournamentDetail>> =>
    apiClient.get(`/api/v1/tournaments/${id}`),

  create: (data: {
    name: string;
    game: GameType;
    format: string;
    max_teams?: number;
    description?: string;
  }): Promise<ApiResponse<TournamentDetail>> =>
    apiClient.post("/api/v1/tournaments", data),

  update: (
    id: string,
    data: Partial<{ name: string; status: TournamentStatus; description: string }>,
  ): Promise<ApiResponse<TournamentDetail>> =>
    apiClient.patch(`/api/v1/tournaments/${id}`, data),

  register: (id: string, teamId: string, notes?: string): Promise<void> =>
    apiClient.post(`/api/v1/tournaments/${id}/register`, { team_id: teamId, notes }),

  generateBracket: (id: string): Promise<ApiResponse<BracketResponse>> =>
    apiClient.post(`/api/v1/tournaments/${id}/bracket`),

  getBracket: (id: string): Promise<ApiResponse<BracketResponse>> =>
    apiClient.get(`/api/v1/tournaments/${id}/bracket`),
};
