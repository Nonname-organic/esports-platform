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

// ── Competitive 集計 ─────────────────────────────────────────────────────────
export interface CompetitiveRank {
  current_rank: string | null;
  peak_rank: string | null;
  peak_rr: number | null;
  current_rr: number | null;
  episode: string | null;
  act: string | null;
}

export interface CompetitiveSummary {
  matches: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_kills: number;
  avg_deaths: number;
  avg_assists: number;
  kd: number;
  kda: number;
  acs: number;
  hs_rate: number | null;
  recent20_win_rate: number;
  adr: number | null;
  kast: number | null;
  fk_rate: number | null;
  fd_rate: number | null;
  clutch_rate: number | null;
  damage_per_round: number | null;
  mvp_rate: number | null;
}

export interface CompetitiveAgent {
  agent: string;
  games: number;
  wins: number;
  win_rate: number;
  pick_rate: number;
  acs: number;
  kd: number;
  kda: number;
  hs_rate: number | null;
  avg_kills: number;
  avg_deaths: number;
  avg_assists: number;
}

export interface CompetitiveMap {
  map: string;
  games: number;
  wins: number;
  win_rate: number;
  acs: number;
  kd: number;
  kda: number;
  attack_win_rate: number | null;
  defense_win_rate: number | null;
  first_kill_rate: number | null;
}

export interface CompetitiveMatch {
  match_id: string;
  agent: string | null;
  map_name: string | null;
  kills: number;
  deaths: number;
  assists: number;
  kd: number;
  kda: number;
  acs: number | null;
  adr: number | null;
  hs_rate: number | null;
  mmr: number | null;
  won: boolean | null;
  played_at: string | null;
}

export interface CompetitiveData {
  linked: boolean;
  riot_id: string | null;
  synced_at: string | null;
  rank: CompetitiveRank;
  summary: CompetitiveSummary;
  agents: CompetitiveAgent[];
  maps: CompetitiveMap[];
  matches: CompetitiveMatch[];
  rank_history: { episode: string; act: string; rank: string; rr: number }[];
}

export const riotApi = {
  link: (playerId: string, riotId: string): Promise<{ data: any }> =>
    apiClient.post("/api/v1/riot/link", { player_id: playerId, riot_id: riotId }),

  sync: (playerId: string): Promise<{ data: { synced_matches: number; synced_at: string } }> =>
    apiClient.post(`/api/v1/riot/sync/${playerId}`),

  profile: (playerId: string): Promise<{ data: RiotProfile | null }> =>
    apiClient.get(`/api/v1/riot/profile/${playerId}`),

  competitive: (playerId: string): Promise<{ data: CompetitiveData }> =>
    apiClient.get(`/api/v1/riot/competitive/${playerId}`),
};
