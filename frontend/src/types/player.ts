import type { GameType } from "./tournament";

export interface Player {
  id: string;
  user_id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
  country: string | null;
  bio: string | null;
  team_id: string | null;
  team_name: string | null;
  team_tag: string | null;
  team_logo_url: string | null;
  in_game_name: string | null;
  game: GameType;
  agent_specialty: string[] | null;
  role: string | null;
  rating: number;
  peak_rating: number;
  created_at: string;
}

export interface PlayerCareerStats {
  total_matches: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_games: number;
  avg_kills: number;
  avg_deaths: number;
  avg_assists: number;
  avg_kda: number;
  avg_score: number;
  headshot_rate: number;
  first_blood_rate: number;
  most_played_agent: string | null;
  most_played_agent_games: number;
}

export interface PlayerKdaPoint {
  month: string;
  avg_kills: number;
  avg_deaths: number;
  avg_assists: number;
  avg_kda: number;
  matches: number;
}

export interface PlayerWinRatePoint {
  month: string;
  win_rate: number;
  rating: number;
  matches: number;
}

export interface AgentUsage {
  agent: string;
  games: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_kills: number;
  avg_deaths: number;
  avg_assists: number;
  avg_kda: number;
}

export interface PlayerAnalytics {
  kda_history: PlayerKdaPoint[];
  win_rate_history: PlayerWinRatePoint[];
  agent_usage: AgentUsage[];
}

export interface PlayerMatchHistory {
  id: string;
  match_id: string;
  tournament_name: string;
  my_team_name: string | null;
  opponent_team_name: string | null;
  result: "win" | "loss" | null;
  agent: string | null;
  kills: number;
  deaths: number;
  assists: number;
  kda: number;
  score: number;
  headshots: number;
  map_name: string | null;
  played_at: string | null;
}
