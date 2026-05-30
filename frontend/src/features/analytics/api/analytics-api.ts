import { apiClient } from "@/lib/api-client";
import type {
  MapStats,
  CompositionStats,
  RankingEntry,
  PlayerStats,
  AnalyticsWinRate,
  TrendPoint,
  AgentStat,
  PlayerRankingEntry,
  HeatMapCell,
  AnalyticsPeriod,
} from "@/types/analytics";
import type { GameType } from "@/types/tournament";

interface ListResponse<T> { data: T[] }

export const analyticsApi = {
  // ── 既存 ────────────────────────────────────────────────────────────────
  mapStats: (game: GameType): Promise<ListResponse<MapStats>> =>
    apiClient.get(`/api/v1/analytics/maps?game=${game}`),

  compositions: (
    game: GameType,
    minGames = 3,
  ): Promise<ListResponse<CompositionStats>> =>
    apiClient.get(`/api/v1/analytics/compositions?game=${game}&min_games=${minGames}`),

  rankings: (tournamentId: string): Promise<ListResponse<RankingEntry>> =>
    apiClient.get(`/api/v1/analytics/rankings/${tournamentId}`),

  playerStats: (playerId: string, game: GameType): Promise<{ data: PlayerStats }> =>
    apiClient.get(`/api/v1/analytics/players/${playerId}/stats?game=${game}`),

  // ── 新規 ────────────────────────────────────────────────────────────────

  /** 全体 KPI + MAP / Agent 勝率 */
  winRate: (params: {
    game: GameType;
    tournamentId?: string;
    dateFrom?: string;
    dateTo?: string;
    teamId?: string;
  }): Promise<{ data: AnalyticsWinRate }> => {
    const qs = new URLSearchParams({ game: params.game });
    if (params.tournamentId) qs.set("tournament_id", params.tournamentId);
    if (params.dateFrom) qs.set("date_from", params.dateFrom);
    if (params.dateTo) qs.set("date_to", params.dateTo);
    if (params.teamId) qs.set("team_id", params.teamId);
    return apiClient.get(`/api/v1/analytics/winrate?${qs.toString()}`);
  },

  /** トレンドデータ */
  trend: (params: {
    game: GameType;
    period: AnalyticsPeriod;
    tournamentId?: string;
    teamId?: string;
  }): Promise<ListResponse<TrendPoint>> => {
    const qs = new URLSearchParams({ game: params.game, period: params.period });
    if (params.tournamentId) qs.set("tournament_id", params.tournamentId);
    if (params.teamId) qs.set("team_id", params.teamId);
    return apiClient.get(`/api/v1/analytics/trend?${qs.toString()}`);
  },

  /** エージェント統計 */
  agents: (params: {
    game: GameType;
    tournamentId?: string;
    dateFrom?: string;
    dateTo?: string;
  }): Promise<ListResponse<AgentStat>> => {
    const qs = new URLSearchParams({ game: params.game });
    if (params.tournamentId) qs.set("tournament_id", params.tournamentId);
    if (params.dateFrom) qs.set("date_from", params.dateFrom);
    if (params.dateTo) qs.set("date_to", params.dateTo);
    return apiClient.get(`/api/v1/analytics/agents?${qs.toString()}`);
  },

  /** プレイヤーランキング */
  playerRankings: (params: {
    game: GameType;
    tournamentId?: string;
    limit?: number;
  }): Promise<ListResponse<PlayerRankingEntry>> => {
    const qs = new URLSearchParams({ game: params.game });
    if (params.tournamentId) qs.set("tournament_id", params.tournamentId);
    if (params.limit) qs.set("limit", String(params.limit));
    return apiClient.get(`/api/v1/analytics/players?${qs.toString()}`);
  },

  /** MAP × Agent ヒートマップ */
  heatmap: (params: {
    game: GameType;
    tournamentId?: string;
  }): Promise<ListResponse<HeatMapCell>> => {
    const qs = new URLSearchParams({ game: params.game });
    if (params.tournamentId) qs.set("tournament_id", params.tournamentId);
    return apiClient.get(`/api/v1/analytics/heatmap?${qs.toString()}`);
  },
};
