import { apiClient } from "@/lib/api-client";
import type { ApiResponse } from "@/types/tournament";

/** Live Status Bar 用のライブ値。 */
export interface LiveStats {
  ongoing_tournaments: number;
  registration_open_tournaments?: number; // 追加フィールド（後方互換のため任意）
  ongoing_matches: number;
  online_participants: number;
  updated_at: string;
}

/** Statistics Card 用のプラットフォーム累計。 */
export interface PlatformTotals {
  tournaments: number;
  teams: number;
  players: number;
  matches: number;
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
};
