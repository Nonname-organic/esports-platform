import { apiClient } from "@/lib/api-client";
import type { ApiResponse } from "@/types/tournament";

/** Recent Titles の1件（順位 / 大会名 / 終了日）。 */
export interface RecentTitle {
  placement: "champion" | "runner_up" | "top4" | string;
  tournament_id: string;
  tournament_name: string;
  ended_at: string | null;
}

/**
 * 読み取り専用の実績カードDTO（Backend の AchievementCardDTO と対）。
 * 将来 Player / Tournament の実績カードでも同型を流用できるよう汎用に保つ。
 */
export interface AchievementCard {
  team_id: string;
  team_name: string;
  team_tag: string;
  game: string;
  championships: number;
  runner_ups: number;
  top4: number;
  tournaments: number;
  matches: number;
  wins: number;
  losses: number;
  win_rate: number;
  mvps: number;
  recent_titles: RecentTitle[];
  founded_at: string | null;
  updated_at: string;
}

export const achievementApi = {
  teamCard: (id: string): Promise<ApiResponse<AchievementCard>> =>
    apiClient.get(`/api/v1/teams/${id}/achievement-card`),
};
