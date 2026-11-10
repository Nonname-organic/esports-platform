import { apiClient } from "@/lib/api-client";
import type { ApiResponse } from "@/types/tournament";

/** 大会の名簿の行（チームが載せ、本人が承認する。RC4） */
export interface RosterEntry {
  id: string;
  tournament_id: string;
  registration_id: string;
  team_id: string;
  player_id: string;
  default_slot: "starter" | "bench";
  status: "invited" | "accepted" | "declined" | "withdrawn" | "removed" | "expired";
  invited_at: string;
  responded_at: string | null;
  removed_at: string | null;
  reason: string | null;
}

export interface MyRosterInvitation extends RosterEntry {
  tournament_name: string;
  team_name: string;
  roster_locked_at: string | null;
}

export interface LineupEntry {
  id: string;
  team_id: string;
  player_id: string;
  in_game_name: string | null;
  slot: "starter" | "bench";
  source: string;
}

export interface LineupView {
  locked_at: string | null;
  entries: LineupEntry[];
  /** マップの番号 → チーム → そのマップに出た出場登録の行 */
  participants_by_game: Record<string, Record<string, string[]>>;
}

export interface Substitution {
  id: string;
  game_number: number;
  team_id: string;
  kind: "between_maps" | "mid_map" | "fill";
  out_lineup_entry_id: string | null;
  in_lineup_entry_id: string;
  at_round: number | null;
  reason: string | null;
  status: "requested" | "approved" | "rejected";
  requested_at: string;
  approved_at: string | null;
}

export interface ParticipationDispute {
  id: string;
  match_id: string;
  player_id: string;
  reason: string;
  status: "open" | "upheld" | "dismissed";
  created_at: string;
  resolved_at: string | null;
  resolution_note: string | null;
}

const base = (tournamentId: string, registrationId: string) =>
  `/api/v1/tournaments/${tournamentId}/registrations/${registrationId}/roster`;

export const rosterApi = {
  get: (tournamentId: string, registrationId: string): Promise<ApiResponse<RosterEntry[]>> =>
    apiClient.get(base(tournamentId, registrationId)),

  add: (tournamentId: string, registrationId: string,
        data: { player_id: string; default_slot?: "starter" | "bench"; reason?: string }): Promise<ApiResponse<RosterEntry>> =>
    apiClient.post(base(tournamentId, registrationId), data),

  update: (tournamentId: string, registrationId: string, entryId: string,
           data: { default_slot?: "starter" | "bench"; remove?: boolean; reason?: string }): Promise<ApiResponse<RosterEntry>> =>
    apiClient.patch(`${base(tournamentId, registrationId)}/${entryId}`, data),

  myInvitations: (): Promise<ApiResponse<MyRosterInvitation[]>> =>
    apiClient.get("/api/v1/me/roster-invitations"),

  respond: (entryId: string, action: "accept" | "decline" | "withdraw"): Promise<ApiResponse<RosterEntry>> =>
    apiClient.post(`/api/v1/roster-entries/${entryId}/${action}`),

  /** 旧方式（legacy）の未開始の大会を名簿の方式に切り替える（主催者・管理者。一方向） */
  switchToRoster: (tournamentId: string): Promise<ApiResponse<{ id: string; roster_mode: string }>> =>
    apiClient.post(`/api/v1/tournaments/${tournamentId}/roster-mode`),

  lineups: (matchId: string): Promise<ApiResponse<LineupView>> =>
    apiClient.get(`/api/v1/matches/${matchId}/lineups`),

  substitutions: (matchId: string): Promise<ApiResponse<Substitution[]>> =>
    apiClient.get(`/api/v1/matches/${matchId}/substitutions`),

  submitSubstitution: (matchId: string, gameNumber: number, data: {
    team_id: string; kind: Substitution["kind"]; out_player_id?: string | null; in_player_id: string;
    at_round?: number | null; reason?: string;
  }): Promise<ApiResponse<Substitution>> =>
    apiClient.post(`/api/v1/matches/${matchId}/games/${gameNumber}/substitutions`, data),

  decideSubstitution: (matchId: string, subId: string, decision: "approve" | "reject"): Promise<ApiResponse<Substitution>> =>
    apiClient.post(`/api/v1/matches/${matchId}/substitutions/${subId}/${decision}`),

  /** 出場登録・成績に載った本人の「出場していない」の異議（C5） */
  createDispute: (matchId: string, reason: string): Promise<ApiResponse<ParticipationDispute>> =>
    apiClient.post("/api/v1/me/participation-disputes", { match_id: matchId, reason }),

  listDisputes: (status?: ParticipationDispute["status"]): Promise<ApiResponse<ParticipationDispute[]>> =>
    apiClient.get(`/api/v1/admin/participation-disputes${status ? `?status=${status}` : ""}`),

  resolveDispute: (id: string, status: "upheld" | "dismissed", note?: string): Promise<ApiResponse<ParticipationDispute>> =>
    apiClient.patch(`/api/v1/admin/participation-disputes/${id}`, { status, note }),

  /** 開始を経ない不戦勝（スターターのいないチームの試合。Q04） */
  forfeitWithoutStart: (matchId: string, winnerId: string, reason: string): Promise<void> =>
    apiClient.post(`/api/v1/matches/${matchId}/forfeit`, { winner_id: winnerId, reason }),
};
