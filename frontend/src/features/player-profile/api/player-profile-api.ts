import { apiClient } from "@/lib/api-client";
import type { ApiResponse } from "@/types/tournament";

export interface PlayerAnalysis {
  provider: string;
  play_style: string;
  strengths: string[];
  weaknesses: string[];
  recommended_role: string | null;
  recommended_agent: string | null;
  consistency: number;
  aggression: number;
  summary: string;
}

export interface PlayerHistoryItem {
  tournament_id: string;
  tournament_name: string;
  game: string;
  ended_at: string | null;
  placement: string | null;
  team_name: string | null;
  is_mvp: boolean;
}

export const playerProfileApi = {
  analysis: (id: string): Promise<ApiResponse<PlayerAnalysis>> =>
    apiClient.get(`/api/v1/players/${id}/analysis`),
  history: (id: string): Promise<ApiResponse<PlayerHistoryItem[]>> =>
    apiClient.get(`/api/v1/players/${id}/history`),
};
