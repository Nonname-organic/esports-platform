import { apiClient } from "@/lib/api-client";
import type { ApiResponse } from "@/types/tournament";

export interface HomeRecommendation {
  id: string;
  name: string;
  game: string;
  banner_url: string | null;
  prize_pool: number | null;
  prize_currency: string;
  registration_end_at: string | null;
  start_at: string | null;
  registered: number;
  max_teams: number;
  fill: number;
  reason: string;
}

export interface PredictionContender {
  team_id: string;
  team_name: string;
  team_tag: string;
  logo_url: string | null;
  win_prob: number;
}

export interface HomePredictions {
  method: string;
  tournament: { id: string; name: string; game: string };
  favorite: PredictionContender | null;
  contenders: PredictionContender[];
  dark_horse: PredictionContender | null;
}

export interface HomeTrending {
  tournaments: { id: string; name: string; game: string; registered: number; max_teams: number }[];
  teams: { team_id: string; team_name: string; rp: number; tier_label: string; tier_color: string }[];
  players: { player_id: string; in_game_name: string; rp: number; tier_label: string; tier_color: string }[];
  tags: { slug: string; label: string; count: number }[];
}

export interface HomeInsight { icon: string; text: string }

export interface HomeData {
  recommendations: HomeRecommendation[];
  predictions: HomePredictions | null;
  trending: HomeTrending;
  live: { live?: Record<string, number>; totals?: Record<string, number> };
  activity: { id: string; type: string; title: string; metadata: Record<string, unknown>; occurred_at: string }[];
  insights: HomeInsight[];
  updated_at: string;
}

export const homeApi = {
  home: (game?: string): Promise<ApiResponse<HomeData>> =>
    apiClient.get(`/api/v1/home${game ? `?game=${game}` : ""}`),
};
