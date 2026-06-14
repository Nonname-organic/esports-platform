export type GameType = "VALORANT" | "LOL" | "APEX" | "CS2" | "OVERWATCH";
export type TournamentFormat = "single_elimination" | "double_elimination" | "round_robin" | "swiss";
export type TournamentStatus =
  | "draft"
  | "registration_open"
  | "registration_closed"
  | "check_in"
  | "ongoing"
  | "completed"
  | "cancelled";

export interface TournamentSummary {
  id: string;
  name: string;
  game: GameType;
  format: TournamentFormat;
  status: TournamentStatus;
  max_teams: number;
  registered_teams: number;
  registration_start_at: string | null;
  registration_end_at: string | null;
  start_at: string | null;
  end_at: string | null;
  prize_pool: number | null;
  banner_url: string | null;
}

export interface TournamentDetail extends TournamentSummary {
  description: string | null;
  rules: Record<string, unknown> | null;
  organizer_id: string;
  registration_start_at: string | null;
  registration_end_at: string | null;
  check_in_start_at: string | null;
  end_at: string | null;
  require_check_in: boolean;
  created_at: string;
  updated_at: string;
}

export interface BracketMatchTeam {
  id: string | null;
  name: string | null;
  tag: string | null;
  logo_url: string | null;
}

export type BracketSide = "winners" | "losers" | "grand_finals";

export interface BracketMatch {
  id: string;
  round_number: number;
  match_number: number;
  team1: BracketMatchTeam | null;
  team2: BracketMatchTeam | null;
  team1_seed: number | null;
  team2_seed: number | null;
  winner_id: string | null;
  status: string;
  scheduled_at: string | null;
  bracket_side: BracketSide | null;
}

export interface BracketResponse {
  tournament_id: string;
  format: TournamentFormat;
  rounds: Record<number, BracketMatch[]>;
}

export interface ListResponse<T> {
  data: T[];
  meta: {
    total: number | null;
    cursor: string | null;
    has_next: boolean;
  };
}

export interface ApiResponse<T> {
  data: T;
  meta: null;
}
