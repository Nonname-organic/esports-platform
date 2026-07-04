import { apiClient } from "@/lib/api-client";
import type { ApiResponse } from "@/types/tournament";

export interface SearchHit {
  type: "team" | "player" | "tournament" | "match";
  id: string;
  label: string;
  sub: string | null;
  image_url: string | null;
  url: string;
  score: number;
}

export interface SearchResults {
  players: SearchHit[];
  teams: SearchHit[];
  tournaments: SearchHit[];
  matches: SearchHit[];
}

export const searchApi = {
  search: (q: string): Promise<ApiResponse<SearchResults>> =>
    apiClient.get(`/api/v1/search?q=${encodeURIComponent(q)}`),
};
