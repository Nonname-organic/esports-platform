export type MatchStatus = "scheduled" | "ongoing" | "completed" | "cancelled" | "forfeit" | "no_show";
export type BOFormat = "BO1" | "BO3" | "BO5";

export interface MatchTeam {
  id: string;
  name: string;
  tag: string;
  logo_url: string | null;
}

export interface PlayerStat {
  player_id: string;
  player_name: string;
  team_id: string;
  agent: string | null;
  kills: number;
  deaths: number;
  assists: number;
  kda: number;
  score: number;
  first_bloods: number;
  custom_stats: Record<string, unknown> | null;
}

export interface MatchGame {
  id: string;
  game_number: number;
  map_id: string | null;
  map_name: string | null;
  team1_score: number;
  team2_score: number;
  winner_id: string | null;
  duration_seconds: number | null;
  player_stats: PlayerStat[];
}

export interface BanPick {
  team_id: string;
  action: "ban" | "pick";
  map_id: string;
  map_name: string;
  order: number;
}

export interface MatchDetail {
  id: string;
  tournament_id: string;
  format: BOFormat;
  status: MatchStatus;
  round_number: number;
  team1: MatchTeam | null;
  team2: MatchTeam | null;
  winner_id: string | null;
  scheduled_at: string | null;
  started_at: string | null;
  ended_at: string | null;
  games: MatchGame[];
  ban_picks: BanPick[];
  stream_url: string | null;
  vod_url: string | null;
}

export interface MatchSummary {
  id: string;
  tournament_id: string;
  format: BOFormat;
  status: MatchStatus;
  round_number: number;
  match_number: number;
  team1: MatchTeam | null;
  team2: MatchTeam | null;
  team1_wins: number;
  team2_wins: number;
  winner_id: string | null;
  scheduled_at: string | null;
  started_at: string | null;
  ended_at: string | null;
  stream_url: string | null;
}

// WebSocket メッセージ
export type WSMessage =
  | { type: "score_update"; match_id: string; game_number: number; team1_score: number; team2_score: number }
  | { type: "match_complete"; match_id: string; winner_id: string; winner_score: number; loser_score: number }
  | { type: "bracket_update"; tournament_id: string; updated_match_id: string }
  | { type: "ping" }
  | { type: "pong" };
