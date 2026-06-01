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

export interface RegistrationInfo {
  id: string;
  team_id: string;
  team_name: string;
  team_tag: string;
  team_logo_url: string | null;
  status: "pending" | "approved" | "rejected" | "withdrawn" | "waitlisted";
  notes: string | null;
  registered_at: string;
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

  mine: (): Promise<ApiResponse<TournamentDetail[]>> =>
    apiClient.get("/api/v1/tournaments/mine"),

  get: (id: string): Promise<ApiResponse<TournamentDetail>> =>
    apiClient.get(`/api/v1/tournaments/${id}`),

  create: (data: {
    name: string;
    game: GameType;
    format: string;
    max_teams?: number;
    description?: string;
    prize_pool?: number;
    registration_start_at?: string;
    registration_end_at?: string;
    check_in_start_at?: string;
    start_at?: string;
    end_at?: string;
    require_check_in?: boolean;
    is_public?: boolean;
    rules?: Record<string, unknown>;
  }): Promise<ApiResponse<TournamentDetail>> =>
    apiClient.post("/api/v1/tournaments", data),

  update: (
    id: string,
    data: Partial<{ name: string; status: TournamentStatus; description: string; prize_pool: number }>,
  ): Promise<ApiResponse<TournamentDetail>> =>
    apiClient.patch(`/api/v1/tournaments/${id}`, data),

  changeStatus: (id: string, status: TournamentStatus): Promise<ApiResponse<TournamentDetail>> =>
    apiClient.patch(`/api/v1/tournaments/${id}/status`, { status }),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/api/v1/tournaments/${id}`),

  register: (id: string, teamId: string, notes?: string): Promise<void> =>
    apiClient.post(`/api/v1/tournaments/${id}/register`, { team_id: teamId, notes }),

  listRegistrations: (id: string): Promise<ApiResponse<RegistrationInfo[]>> =>
    apiClient.get(`/api/v1/tournaments/${id}/registrations`),

  updateRegistration: (
    tournamentId: string,
    registrationId: string,
    status: "approved" | "rejected" | "pending",
  ): Promise<ApiResponse<RegistrationInfo>> =>
    apiClient.patch(
      `/api/v1/tournaments/${tournamentId}/registrations/${registrationId}?status=${status}`,
      {}
    ),

  generateBracket: (id: string): Promise<ApiResponse<BracketResponse>> =>
    apiClient.post(`/api/v1/tournaments/${id}/bracket`),

  getBracket: (id: string): Promise<ApiResponse<BracketResponse>> =>
    apiClient.get(`/api/v1/tournaments/${id}/bracket`),
};
