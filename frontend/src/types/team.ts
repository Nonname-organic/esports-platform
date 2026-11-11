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
  /** RC4: 所属の承諾の状態（self・invitation・confirmed は本人の承諾済み、unconfirmed は移行前の本人未確認） */
  consent?: MembershipConsent;
  /** 正式な所属か（承諾済み、または移行期間中の本人未確認） */
  formal?: boolean;
}

export type MembershipConsent = "self" | "invitation" | "confirmed" | "unconfirmed" | "rejected";

/** チームからの招待（本人が承認したときだけ所属になる） */
export interface TeamInvitation {
  id: string;
  team_id: string;
  invitee_user_id: string;
  role: string;
  status: "pending" | "accepted" | "declined" | "cancelled" | "expired";
  created_at: string;
  expires_at: string;
}

export interface MyTeamInvitation extends TeamInvitation {
  team_name: string;
  team_tag: string;
}

/** 自分の所属（移行前の本人未確認の所属は、本人が確認か否認をする） */
export interface Membership {
  id: string;
  team_id: string;
  team_name: string;
  team_tag: string;
  role: string;
  joined_at: string;
  left_at: string | null;
  consent: MembershipConsent;
  confirmed_at: string | null;
  rejected_at: string | null;
  formal: boolean;
}

export interface MyMemberships {
  /** 本人未確認の所属を数える期限（移行の開始から 60 日）。未設定なら null */
  deadline: string | null;
  items: Membership[];
}

export interface TeamStats {
  total_matches: number;
  wins: number;
  losses: number;
  win_rate: number;
  game_wins: number;
  game_losses: number;
  game_win_rate: number;
  /** ランキング集計がまだ無いチームは null */
  rating: number | null;
  peak_rating: number | null;
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
