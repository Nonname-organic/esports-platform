export type GameType = "VALORANT" | "LOL" | "APEX" | "CS2" | "OVERWATCH";

/**
 * UI上で選択・絞り込みできるゲームタイトル（現在は VALORANT のみ提供）。
 * GameType 自体は過去データとの互換のため他タイトルも残しているため、
 * 「選べるタイトル」を増やす時はこの配列だけを更新する。
 */
export const SELECTABLE_GAMES: { value: GameType; label: string }[] = [
  { value: "VALORANT", label: "VALORANT" },
];
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

export interface TournamentAttachment {
  name: string;
  url: string;
  key: string;
  size?: number;
  content_type?: string;
}

export interface TournamentDetail extends TournamentSummary {
  description: string | null;
  rules: Record<string, unknown> | null;
  attachments: TournamentAttachment[] | null;
  organizer_id: string;
  registration_start_at: string | null;
  registration_end_at: string | null;
  check_in_start_at: string | null;
  end_at: string | null;
  require_check_in: boolean;
  created_at: string;
  updated_at: string;
  // 編集フォームの初期値として読み戻す項目（作成フォームと対応）
  subtitle?: string | null;
  thumbnail_url?: string | null;
  season?: string | null;
  split?: string | null;
  tier?: string | null;
  visibility?: string | null;
  seeding_type?: string | null;
  min_teams?: number | null;
  prize_currency?: string | null;
  require_team_membership?: boolean | null;
  approval_mode?: string | null;
  age_restriction?: Record<string, unknown> | null;
  region_restriction?: Record<string, unknown> | null;
  rank_restriction?: Record<string, unknown> | null;
  discord_webhook_url?: string | null;
  /** Webhookが設定済みか（URL本体はAPIから返さない） */
  discord_webhook_configured?: boolean;
  analytics_enabled?: boolean | null;
  player_stats_enabled?: boolean | null;
  ranking_enabled?: boolean | null;
  is_public?: boolean | null;
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
