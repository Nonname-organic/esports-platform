import { apiClient } from "@/lib/api-client";
import type { ApiResponse } from "@/types/tournament";

export interface ScoutPlayerCard {
  player_id: string;
  in_game_name: string;
  game: string;
  main_role: string | null;
  rank: string | null;
  region: string | null;
  current_team_id: string | null;
  current_team_name: string | null;
  rating: number | null;
  scout_rating: number | null;
  win_rate: number;
  total_matches: number;
  championships: number;
  mvp_count: number;
  tournaments_played: number;
  is_looking: boolean;
  availability: string | null;
  languages: string[] | null;
}

export interface ScoutTeamCard {
  team_id: string;
  name: string;
  tag: string;
  game: string;
  logo_url: string | null;
  region: string | null;
  avg_rating: number | null;
  win_rate: number;
  total_matches: number;
  championships: number;
  roster_count: number;
  is_recruiting: boolean;
}

export interface RecruitmentPost {
  id: string;
  author_id: string;
  post_type: "team_seeks" | "player_seeks";
  team_id: string | null;
  player_id: string | null;
  game: string;
  title: string;
  description: string | null;
  required_roles: string[] | null;
  min_rank: string | null;
  regions: string[] | null;
  is_open: boolean;
  application_count: number;
  created_at: string;
}

export interface RecommendationItem {
  target_id: string;
  target_type: "player" | "team";
  name: string;
  score: number;
  breakdown: Record<string, number>;
  summary: string;
}

export interface PlayerSearchParams {
  game?: string;
  role?: string;
  rank?: string;
  region?: string;
  min_win_rate?: number;
  min_rating?: number;
  min_tournaments?: number;
  looking_only?: boolean;
  sort_by?: string;
}

export const scoutApi = {
  searchPlayers: (params: PlayerSearchParams): Promise<ApiResponse<ScoutPlayerCard[]>> => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "" && v !== false) qs.set(k, String(v));
    });
    return apiClient.get(`/api/v1/scout/players?${qs.toString()}`);
  },

  searchTeams: (params: { game?: string; region?: string; recruiting_only?: boolean }): Promise<ApiResponse<ScoutTeamCard[]>> => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "" && v !== false) qs.set(k, String(v));
    });
    return apiClient.get(`/api/v1/scout/teams?${qs.toString()}`);
  },

  listRecruitment: (params?: { post_type?: string; game?: string }): Promise<ApiResponse<RecruitmentPost[]>> => {
    const qs = new URLSearchParams();
    if (params?.post_type) qs.set("post_type", params.post_type);
    if (params?.game) qs.set("game", params.game);
    return apiClient.get(`/api/v1/scout/recruitment${qs.toString() ? `?${qs}` : ""}`);
  },

  createRecruitment: (data: {
    post_type: string; game: string; title: string; description?: string;
    team_id?: string; player_id?: string; required_roles?: string[]; min_rank?: string; regions?: string[];
  }): Promise<ApiResponse<RecruitmentPost>> =>
    apiClient.post("/api/v1/scout/recruitment", data),

  deleteRecruitment: (id: string): Promise<void> =>
    apiClient.delete(`/api/v1/scout/recruitment/${id}`),

  apply: (data: { post_id: string; kind?: string; message?: string; player_id?: string; team_id?: string }): Promise<ApiResponse<unknown>> =>
    apiClient.post("/api/v1/scout/recruitment/apply", data),

  recommendTeams: (playerId: string): Promise<ApiResponse<RecommendationItem[]>> =>
    apiClient.get(`/api/v1/scout/recommendations/teams/${playerId}`),

  recommendPlayers: (teamId: string): Promise<ApiResponse<RecommendationItem[]>> =>
    apiClient.get(`/api/v1/scout/recommendations/players/${teamId}`),
};
