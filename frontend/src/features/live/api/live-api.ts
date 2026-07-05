import { apiClient } from "@/lib/api-client";
import type { ApiResponse } from "@/types/tournament";

/** Live Status Bar 用のライブ値。 */
export interface LiveStats {
  ongoing_tournaments: number;
  registration_open_tournaments?: number; // 追加フィールド（後方互換のため任意）
  ongoing_matches: number;
  online_participants: number;
  entries_today?: number;   // FOMO: 本日のエントリー数
  entries_recent?: number;  // FOMO: 直近5分のエントリー数
  updated_at: string;
}

/** Statistics Card / Social Proof 用のプラットフォーム累計。 */
export interface PlatformTotals {
  tournaments: number;
  teams: number;
  players: number;
  matches: number;
  champions?: number; // 追加フィールド（後方互換のため任意）
  mvps?: number;
}

/** Winner Showcase 用の直近優勝チーム。 */
export interface RecentChampion {
  tournament_id: string;
  tournament_name: string;
  game: string;
  champion_team_id: string | null;
  champion_team_name: string | null;
  runner_up_name?: string | null;
  mvp_name: string | null;
  prize?: number | null;
  prize_currency?: string;
  banner_url?: string | null;
  ended_at: string | null;
}

export interface StatsOverview {
  live: LiveStats;
  totals: PlatformTotals;
}

/** Live Activity フィードの1件（公開イベント）。 */
export interface LiveActivityItem {
  id: string;
  type: string;
  title: string;
  metadata: Record<string, unknown>;
  occurred_at: string;
}

export const liveApi = {
  overview: (): Promise<ApiResponse<StatsOverview>> =>
    apiClient.get(`/api/v1/stats/overview`),
  feed: (limit = 20): Promise<ApiResponse<LiveActivityItem[]>> =>
    apiClient.get(`/api/v1/activity/feed?limit=${limit}`),
  champions: (limit = 3): Promise<ApiResponse<RecentChampion[]>> =>
    apiClient.get(`/api/v1/stats/champions?limit=${limit}`),
};
