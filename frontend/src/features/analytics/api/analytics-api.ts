import { apiClient } from "@/lib/api-client";
import type { MapStats, CompositionStats, RankingEntry, PlayerStats } from "@/types/analytics";
import type { GameType } from "@/types/tournament";

interface AnalyticsListResponse<T> {
  data: T[];
}

export const analyticsApi = {
  mapStats: (game: GameType): Promise<AnalyticsListResponse<MapStats>> =>
    apiClient.get(`/api/v1/analytics/maps?game=${game}`),

  compositions: (game: GameType, minGames = 3): Promise<AnalyticsListResponse<CompositionStats>> =>
    apiClient.get(`/api/v1/analytics/compositions?game=${game}&min_games=${minGames}`),

  rankings: (tournamentId: string): Promise<AnalyticsListResponse<RankingEntry>> =>
    apiClient.get(`/api/v1/analytics/rankings/${tournamentId}`),

  playerStats: (playerId: string, game: GameType): Promise<{ data: PlayerStats }> =>
    apiClient.get(`/api/v1/analytics/players/${playerId}/stats?game=${game}`),
};
