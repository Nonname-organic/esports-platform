import { apiClient } from "@/lib/api-client";
import type {
  ApiResponse,
  BracketResponse,
  ListResponse,
  TournamentDetail,
  TournamentSummary,
  TournamentAttachment,
  GameType,
  TournamentStatus,
} from "@/types/tournament";

export type TournamentSortOrder = "start_at_asc" | "start_at_desc" | "created_at_desc";

export interface TournamentListParams {
  q?: string;
  game?: GameType;
  status?: TournamentStatus;
  sort?: TournamentSortOrder;
  month?: string; // "YYYY-MM"。その月に受付/開催する大会のみ
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
    if (params?.month) qs.set("month", params.month);
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
    check_in_end_at?: string;
    start_at?: string;
    end_at?: string;
    require_check_in?: boolean;
    is_public?: boolean;
    /** manual=主催者が個別承認 / auto=先着順で自動承認 */
    approval_mode?: string;
    rules?: Record<string, unknown>;
    attachments?: TournamentAttachment[];
  }): Promise<ApiResponse<TournamentDetail>> =>
    apiClient.post("/api/v1/tournaments", data),

  uploadFile: (file: File): Promise<{ url: string; key: string; name: string; size: number; content_type: string }> => {
    const fd = new FormData();
    fd.append("file", file);
    return apiClient.upload("/api/v1/upload/file?purpose=tournament_attachment", fd);
  },

  /** 大会情報の更新。作成フォームで設定した項目をすべて後から編集できる。 */
  update: (
    id: string,
    data: Partial<{
      name: string;
      status: TournamentStatus;
      description: string;
      prize_pool: number;
      prize_currency: string;
      max_teams: number;
      min_teams: number;
      format: string;
      registration_start_at: string;
      registration_end_at: string;
      check_in_start_at: string;
      check_in_end_at?: string;
      start_at: string;
      end_at: string;
      is_public: boolean;
      require_check_in: boolean;
      require_team_membership: boolean;
      approval_mode: string;
      attachments: TournamentAttachment[];
      subtitle: string;
      banner_url: string;
      thumbnail_url: string;
      season: string;
      split: string;
      tier: string;
      visibility: string;
      seeding_type: string;
      discord_webhook_url: string;
      age_restriction: Record<string, unknown>;
      region_restriction: Record<string, unknown>;
      rank_restriction: Record<string, unknown>;
      analytics_enabled: boolean;
      player_stats_enabled: boolean;
      ranking_enabled: boolean;
      /** 賞金内訳・配信・Discord・スポンサー・連絡先などの拡張項目（丸ごと差し替え） */
      rules: Record<string, unknown>;
    }>,
  ): Promise<ApiResponse<TournamentDetail>> =>
    apiClient.patch(`/api/v1/tournaments/${id}`, data),

  changeStatus: (id: string, status: TournamentStatus): Promise<ApiResponse<TournamentDetail>> =>
    apiClient.patch(`/api/v1/tournaments/${id}/status`, { status }),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/api/v1/tournaments/${id}`),

  /** 参加申請。自動承認の大会では approved / 定員超過時は waitlisted が返る。 */
  register: (id: string, teamId: string, notes?: string): Promise<ApiResponse<{ status: string }>> =>
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
