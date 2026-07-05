import { apiClient } from "@/lib/api-client";
import type { ApiResponse, ListResponse } from "@/types/tournament";

export interface TierInfo {
  key: string;
  label: string;
  min_rp: number;
  color: string;
  icon: string;
}

export interface SeasonInfo {
  key: string;
  id: string;
  label: string;
  start_at: string | null;
  end_at: string | null;
  is_current: boolean;
}

export interface SeasonRankItem {
  key: string;
  label: string;
  rp: number;
  rank: number | null;
  tier_label: string;
  tier_color: string;
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
  progress: number;
  tournaments: number;
  championships: number;
  runner_ups: number;
  top4: number;
  wins: number;
  losses: number;
  win_rate: number;
}

export interface PlayerLeaderboardEntry {
  rank: number;
  player_id: string;
  in_game_name: string;
  game: string;
  rp: number;
  tier_key: string;
  tier_label: string;
  tier_color: string;
  progress: number;
  mvps: number;
}

export interface RankHistoryItem {
  tournament_id: string;
  tournament_name: string;
  ended_at: string | null;
  placement: string;
  rp_gained: number;
  cumulative_rp: number;
}

/** チーム/プレイヤー共通の RankCard（同一 SSOT / ADR-0016）。 */
export interface RankCard {
  team_id?: string;
  team_name?: string;
  team_tag?: string;
  player_id?: string;
  in_game_name?: string;
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
  tournaments?: number;
  current_season_rp: number;
  previous_season_rp: number;
  best_season_tier: string | null;
  best_season_tier_color: string | null;
  matches: number;
  wins: number;
  losses: number;
  win_rate: number;
  mvps?: number;
  seasons: SeasonRankItem[];
  history?: RankHistoryItem[];
}

export type SeasonScope = "all" | "current" | "previous";

export const rankingApi = {
  tiers: (): Promise<ApiResponse<TierInfo[]>> => apiClient.get(`/api/v1/rankings/tiers`),
  seasons: (): Promise<ApiResponse<SeasonInfo[]>> => apiClient.get(`/api/v1/seasons`),
  global: (params: { game?: string; season?: SeasonScope; limit?: number } = {}): Promise<ListResponse<LeaderboardEntry>> =>
    apiClient.get(`/api/v1/rankings/global${qs(params)}`),
  players: (params: { game?: string; season?: SeasonScope; limit?: number } = {}): Promise<ListResponse<PlayerLeaderboardEntry>> =>
    apiClient.get(`/api/v1/rankings/players${qs(params)}`),
  teamRankCard: (teamId: string): Promise<ApiResponse<RankCard>> =>
    apiClient.get(`/api/v1/teams/${teamId}/rank-card`),
  playerRankCard: (playerId: string): Promise<ApiResponse<RankCard>> =>
    apiClient.get(`/api/v1/players/${playerId}/rank-card`),
};

function qs(params: { game?: string; season?: SeasonScope; limit?: number }): string {
  const p = new URLSearchParams();
  if (params.game) p.set("game", params.game);
  if (params.season) p.set("season", params.season);
  if (params.limit) p.set("limit", String(params.limit));
  const s = p.toString();
  return s ? `?${s}` : "";
}
