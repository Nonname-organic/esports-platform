import { apiClient } from "@/lib/api-client";
import type { ApiResponse } from "@/types/tournament";

export interface AgentUsageItem {
  agent: string;
  games: number;
  wins: number;
  win_rate: number;
  avg_kda: number;
}

export interface MapPerformanceItem {
  map_name: string;
  games: number;
  wins: number;
  win_rate: number;
}

export interface AchievementItem {
  id: string;
  type: string;
  title: string;
  description: string | null;
  icon_url: string | null;
  tournament_id: string | null;
  earned_at: string;
}

export interface RatingPoint {
  date: string;
  rating: number;
  delta: number;
}

export interface PlayerCareer {
  player_id: string;
  in_game_name: string;
  game: string;
  total_matches: number;
  total_wins: number;
  total_losses: number;
  win_rate: number;
  championships: number;
  mvp_count: number;
  tournaments_played: number;
  current_rating: number | null;
  peak_rating: number | null;
  avg_acs: number;
  avg_kda: number;
  avg_kills: number;
  avg_deaths: number;
  avg_assists: number;
  agent_usage: AgentUsageItem[];
  map_performance: MapPerformanceItem[];
}

export interface RivalItem {
  team_id: string;
  team_name: string;
  team_tag: string;
  matches: number;
  wins: number;
  losses: number;
  win_rate: number;
}

export interface TeamCareer {
  team_id: string;
  team_name: string;
  team_tag: string;
  game: string;
  total_matches: number;
  total_wins: number;
  total_losses: number;
  win_rate: number;
  championships: number;
  tournaments_played: number;
  current_rating: number | null;
  peak_rating: number | null;
  map_performance: MapPerformanceItem[];
  agent_trends: AgentUsageItem[];
  rivals: RivalItem[];
}

export const careerApi = {
  playerCareer: (id: string): Promise<ApiResponse<PlayerCareer>> =>
    apiClient.get(`/api/v1/players/${id}/career`),
  playerAchievements: (id: string): Promise<ApiResponse<AchievementItem[]>> =>
    apiClient.get(`/api/v1/players/${id}/achievements`),
  playerRatingHistory: (id: string, game: string): Promise<ApiResponse<RatingPoint[]>> =>
    apiClient.get(`/api/v1/players/${id}/rating-history?game=${game}`),

  teamCareer: (id: string): Promise<ApiResponse<TeamCareer>> =>
    apiClient.get(`/api/v1/teams/${id}/career`),
  teamAchievements: (id: string): Promise<ApiResponse<AchievementItem[]>> =>
    apiClient.get(`/api/v1/teams/${id}/achievements`),
  teamRivals: (id: string): Promise<ApiResponse<RivalItem[]>> =>
    apiClient.get(`/api/v1/teams/${id}/rivals`),
};
