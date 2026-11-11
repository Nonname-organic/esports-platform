import { apiClient } from "@/lib/api-client";
import type {
  MatchDetail,
  MatchStatus,
  MatchSummary,
  ScoreboardParseResult,
} from "@/types/match";
import type { ApiResponse, ListResponse } from "@/types/tournament";

export const matchApi = {
  get: (id: string): Promise<ApiResponse<MatchDetail>> =>
    apiClient.get(`/api/v1/matches/${id}`),

  listByTournament: (
    tournamentId: string,
    params?: { status?: MatchStatus; limit?: number; cursor?: string },
  ): Promise<ListResponse<MatchSummary>> => {
    const qs = new URLSearchParams({ tournament_id: tournamentId });
    if (params?.status) qs.set("status", params.status);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.cursor) qs.set("cursor", params.cursor);
    return apiClient.get(`/api/v1/matches?${qs.toString()}`);
  },

  /** 開始で出場登録を固定する。スターターが出場人数に満たないチームがあれば理由が要る（RC4） */
  start: (id: string, reason?: string): Promise<void> =>
    apiClient.patch(`/api/v1/matches/${id}/start`, reason ? { reason } : undefined),

  /** この試合を配信対象にする。空文字で解除。 */
  setStreamUrl: (id: string, streamUrl: string): Promise<unknown> =>
    apiClient.patch(`/api/v1/matches/${id}/stream`, { stream_url: streamUrl }),

  updateScore: (
    id: string,
    gameNumber: number,
    data: { team1_score: number; team2_score: number; duration_seconds?: number },
  ): Promise<void> =>
    apiClient.post(`/api/v1/matches/${id}/games/${gameNumber}/score`, data),

  registerResult: (
    id: string,
    data: {
      winner_id: string;
      was_forfeit?: boolean;
      game_stats?: unknown[];
      /** 完了・中止した大会の訂正（管理者だけ）の理由（RC4） */
      correction_reason?: string;
    },
  ): Promise<void> => apiClient.post(`/api/v1/matches/${id}/result`, data),

  // 対戦チームによる結果報告 → 相手チームの確認（主催者は報告で即確定）
  reportState: (id: string): Promise<{ data: ResultReportState }> =>
    apiClient.get(`/api/v1/matches/${id}/report`),
  report: (id: string, winnerId: string): Promise<{ data: { status: string } }> =>
    apiClient.post(`/api/v1/matches/${id}/report`, { winner_id: winnerId }),
  confirmReport: (id: string): Promise<{ data: { status: string } }> =>
    apiClient.post(`/api/v1/matches/${id}/report/confirm`),
  disputeReport: (id: string, reason: string): Promise<{ data: { status: string } }> =>
    apiClient.post(`/api/v1/matches/${id}/report/dispute`, { reason }),
  /** 完了・中止した大会の試合は、管理者だけが理由つきで再開できる（RC4） */
  reopen: (id: string, reason?: string): Promise<void> =>
    apiClient.post(`/api/v1/matches/${id}/reopen`, reason ? { reason } : undefined),

  registerBanPick: (
    id: string,
    data: { team_id: string; action: "ban" | "pick"; map_id: string; order: number },
  ): Promise<void> => apiClient.post(`/api/v1/matches/${id}/banpick`, data),

  /** 1マップ分のスコアと選手成績を保存する（スコアボード取り込みの確定） */
  saveGamePlayerStats: (
    id: string,
    gameNumber: number,
    data: {
      map_id?: string | null;
      team1_score: number;
      team2_score: number;
      player_stats: {
        player_id: string;
        team_id: string;
        agent: string | null;
        kills: number;
        deaths: number;
        assists: number;
        score: number;
        first_bloods: number;
      }[];
    },
  ): Promise<void> =>
    apiClient.post(`/api/v1/matches/${id}/games/${gameNumber}/player-stats`, data),

  /** スコアボード画像を解析して選手成績の候補を取得する（この時点では未保存） */
  parseScoreboard: (
    id: string,
    file: File,
  ): Promise<ApiResponse<ScoreboardParseResult>> => {
    const form = new FormData();
    form.append("file", file);
    return apiClient.upload(`/api/v1/matches/${id}/scoreboard-ocr`, form);
  },
};

export interface ResultReportState {
  report: {
    status: "pending" | "confirmed" | "disputed" | "superseded";
    winner_id: string;
    reported_by_team_id: string;
    dispute_reason: string | null;
  } | null;
  my_team_id: string | null;
  can_report: boolean;
  can_confirm: boolean;
  can_dispute: boolean;
}
