import type { GameType } from "./tournament";

export interface PlayerStats {
  player_id: string;
  in_game_name: string;
  game: GameType;
  period_type: string;
  period_date: string;
  matches_played: number;
  matches_won: number;
  games_played: number;
  games_won: number;
  total_kills: number;
  total_deaths: number;
  total_assists: number;
  avg_kda: number;
  win_rate: number;
  most_played_agent: string | null;
  agent_breakdown: Record<string, { games: number; wins: number; kda: number }> | null;
}

export interface MapStats {
  map_id: string;
  map_name: string;
  game: GameType;
  total_games: number;
  attack_side_wins: number;
  defense_side_wins: number;
  attack_win_rate: number;
  avg_duration_seconds: number | null;
  round_distribution: Record<string, number> | null;
}

export interface CompositionStats {
  composition: string[];
  games_played: number;
  wins: number;
  win_rate: number;
  avg_kills: number | null;
  avg_deaths: number | null;
}

export interface RankingEntry {
  rank_position: number;
  team_id: string;
  team_name: string;
  team_tag: string;
  team_logo_url: string | null;
  points: number;
  wins: number;
  losses: number;
  game_wins: number;
  game_losses: number;
  win_rate: number;
}

export interface TournamentSummary {
  tournament_id: string;
  tournament_name: string;
  game: GameType;
  total_matches: number;
  completed_matches: number;
  total_teams: number;
  top_teams: Array<{ team_id: string; team_name: string; wins: number }>;
  top_players_kda: Array<{ player_id: string; avg_kda: number }>;
  most_played_map: string | null;
  avg_match_duration_seconds: number | null;
}
