import { apiClient } from "@/lib/api-client";
import type { ApiResponse, ListResponse } from "@/types/tournament";

export interface TierInfo {
  key: string;
  label: string;
  min_rp: number;
  color: string;
  icon: string;
}

export interface LeaderboardEntry {
  rank: number;
  team_id: string;
  team_name: string;
  team_tag: string;
  team_logo_url: string | null;
  game: string;
  rp: number;
  tier_key: string;
  tier_label: string;
  tier_color: string;
  tournaments: number;
  championships: number;
  wins: number;
  losses: number;
  win_rate: number;
}

export interface RankCard {
  team_id: string;
  team_name: string;
  team_tag: string;
  game: string;
  rp: number;
  rank: number | null;
  total_ranked: number;
  tier_key: string;
  tier_label: string;
  tier_color: string;
  next_tier_label: string | null;
  next_tier_rp: number | null;
  progress: number;
  championships: number;
  tournaments: number;
}

export type SeasonScope = "all" | "current";

export const rankingApi = {
  tiers: (): Promise<ApiResponse<TierInfo[]>> => apiClient.get(`/api/v1/rankings/tiers`),
  global: (params: { game?: string; season?: SeasonScope; limit?: number } = {}): Promise<ListResponse<LeaderboardEntry>> => {
    const qs = new URLSearchParams();
    if (params.game) qs.set("game", params.game);
    if (params.season) qs.set("season", params.season);
    if (params.limit) qs.set("limit", String(params.limit));
    const q = qs.toString();
    return apiClient.get(`/api/v1/rankings/global${q ? `?${q}` : ""}`);
  },
  teamCard: (teamId: string, season: SeasonScope = "all"): Promise<ApiResponse<RankCard>> =>
    apiClient.get(`/api/v1/rankings/team/${teamId}?season=${season}`),
};
