import type { GameType } from "./tournament";

export type TeamRole = "player" | "coach" | "analyst" | "manager" | "substitute";

export interface Team {
  id: string;
  owner_id: string;
  name: string;
  tag: string;
  logo_url: string | null;
  banner_url: string | null;
  game: GameType;
  region: string | null;
  country: string | null;
  founded_at: string | null;
  description: string | null;
  social_links: {
    twitter?: string;
    twitch?: string;
    discord?: string;
    website?: string;
  } | null;
  rating: number;
  created_at: string;
  updated_at: string;
}

export interface TeamMember {
  id: string;
  player_id: string;
  user_id: string | null;
  username: string | null;
  display_name: string | null;
  avatar_url: string | null;
  role: TeamRole;
  in_game_name: string | null;
  jersey_number: number | null;
  agent_specialty: string[] | null;
  joined_at: string;
  is_active: boolean;
  rating: number | null;
}

export interface TeamStats {
  total_matches: number;
  wins: number;
  losses: number;
  win_rate: number;
  game_wins: number;
  game_losses: number;
  game_win_rate: number;
  rating: number;
  peak_rating: number;
  tournaments_played: number;
  tournaments_won: number;
  current_streak: number;
  best_streak: number;
}

export interface WinRatePoint {
  month: string;
  win_rate: number;
  rating: number;
  matches: number;
}

export interface MonthlyStatsPoint {
  month: string;
  wins: number;
  losses: number;
  tournaments: number;
}

export interface TeamAnalytics {
  win_rate_history: WinRatePoint[];
  monthly_stats: MonthlyStatsPoint[];
}

export interface TeamMatchSummary {
  id: string;
  tournament_id: string;
  tournament_name: string;
  opponent: {
    id: string;
    name: string;
    tag: string;
    logo_url: string | null;
  } | null;
  result: "win" | "loss" | null;
  team_score: number;
  opponent_score: number;
  status: string;
  played_at: string | null;
  format: string;
}
