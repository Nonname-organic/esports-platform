import { apiClient } from "@/lib/api-client";
import type { ApiResponse } from "@/types/tournament";

export interface ImmersionTeam {
  id: string;
  name: string;
  tag: string;
  logo_url: string | null;
}

export interface ImmersionMatch {
  id: string;
  round_number: number;
  status: string;
  format: string;
  scheduled_at: string | null;
  stream_url: string | null;
  team1: ImmersionTeam | null;
  team2: ImmersionTeam | null;
  score1: number;
  score2: number;
  current_game: { game_number: number; map: string | null; t1_rounds: number; t2_rounds: number } | null;
}

export interface TournamentOverview {
  id: string;
  name: string;
  game: string;
  format: string;
  status: string;
  banner_url: string | null;
  prize_pool: number | null;
  prize_currency: string;
  start_at: string | null;
  end_at: string | null;
  registration_end_at: string | null;
  max_teams: number;
  registered_teams: number;
  current_match: ImmersionMatch | null;
  stream: { url: string; platform: string; is_live: boolean } | null;
  result: { champion: { team_name?: string } | null; runner_up: { team_name?: string } | null; mvp: string | null } | null;
  updated_at: string;
}

export interface TournamentLive {
  status: string;
  total_matches: number;
  completed_matches: number;
  ongoing_matches: number;
  scheduled_matches: number;
  remaining_matches: number;
  progress: number;
  current_round: number | null;
  start_at: string | null;
  end_at: string | null;
  current_match: ImmersionMatch | null;
  live_matches: ImmersionMatch[];
  upcoming: ImmersionMatch[];
  updated_at: string;
}

export interface TournamentStatistics {
  participants: number;
  max_teams: number;
  matches: number;
  completed_matches: number;
  completion_rate: number;
  prize_pool: number | null;
  prize_currency: string;
  mvp: string | null;
  champion: { team_name?: string } | null;
  updated_at: string;
}

export const tournamentLiveApi = {
  overview: (id: string): Promise<ApiResponse<TournamentOverview>> =>
    apiClient.get(`/api/v1/tournaments/${id}/overview`),
  live: (id: string): Promise<ApiResponse<TournamentLive>> =>
    apiClient.get(`/api/v1/tournaments/${id}/live`),
  statistics: (id: string): Promise<ApiResponse<TournamentStatistics>> =>
    apiClient.get(`/api/v1/tournaments/${id}/statistics`),
};
