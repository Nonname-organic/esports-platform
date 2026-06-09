import { apiClient } from "@/lib/api-client";

export interface RiotMatch {
  match_id: string;
  agent: string | null;
  map_name: string | null;
  kills: number;
  deaths: number;
  assists: number;
  acs: number | null;
  won: boolean | null;
}

export interface RiotProfile {
  player_id: string;
  riot_id: string;
  puuid: string | null;
  region: string | null;
  current_rank: string | null;
  peak_rank: string | null;
  synced_at: string | null;
  matches: RiotMatch[];
}

export const riotApi = {
  link: (playerId: string, riotId: string): Promise<{ data: any }> =>
    apiClient.post("/api/v1/riot/link", { player_id: playerId, riot_id: riotId }),

  sync: (playerId: string): Promise<{ data: { synced_matches: number; synced_at: string } }> =>
    apiClient.post(`/api/v1/riot/sync/${playerId}`),

  profile: (playerId: string): Promise<{ data: RiotProfile | null }> =>
    apiClient.get(`/api/v1/riot/profile/${playerId}`),
};
