import { apiClient } from "@/lib/api-client";
import type { ApiResponse, ListResponse } from "@/types/tournament";

export interface LFTPost {
  id: string;
  player_id: string;
  user_id: string;
  in_game_name: string;
  avatar_url: string | null;
  status: "open" | "negotiating" | "closed";
  roles: string[];
  current_rank: string;
  peak_rank: string;
  region: string;
  activity_time: string[];
  experience: string | null;
  premier: string | null;
  agents: string[];
  description: string | null;
  conditions: string | null;
  discord: string | null;
  twitter: string | null;
  deadline: string | null;
  is_public: boolean;
  // 大会実績（一覧APIが競技ランキングから付与 / 未参加者はnull）
  rp?: number | null;
  tier_label?: string | null;
  tier_color?: string | null;
  mvps?: number | null;
  ranking?: number | null;
  created_at: string;
  updated_at: string;
}

export interface LFTCreateInput {
  status?: string;
  roles: string[];
  current_rank: string;
  peak_rank: string;
  region: string;
  activity_time?: string[];
  experience?: string;
  premier?: string;
  agents?: string[];
  description?: string;
  conditions?: string;
  discord?: string;
  twitter?: string;
  deadline?: string;
  is_public?: boolean;
}

export interface LFTSearchParams {
  status?: string;
  region?: string;
  role?: string;
  rank?: string;
  min_rank?: string;
  max_rank?: string;
  limit?: number;
  offset?: number;
}

export const lftApi = {
  list: (params?: LFTSearchParams): Promise<ListResponse<LFTPost>> => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.region) qs.set("region", params.region);
    if (params?.role) qs.set("role", params.role);
    if (params?.rank) qs.set("rank", params.rank);
    if (params?.min_rank) qs.set("min_rank", params.min_rank);
    if (params?.max_rank) qs.set("max_rank", params.max_rank);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    return apiClient.get(`/api/v1/lft${qs.toString() ? `?${qs}` : ""}`);
  },

  getMe: (): Promise<ApiResponse<LFTPost | null>> =>
    apiClient.get("/api/v1/lft/me"),

  get: (id: string): Promise<ApiResponse<LFTPost>> =>
    apiClient.get(`/api/v1/lft/${id}`),

  create: (data: LFTCreateInput): Promise<ApiResponse<LFTPost>> =>
    apiClient.post("/api/v1/lft", data),

  updateMe: (data: Partial<LFTCreateInput>): Promise<ApiResponse<LFTPost>> =>
    apiClient.patch("/api/v1/lft/me", data),

  deleteMe: (): Promise<void> =>
    apiClient.delete("/api/v1/lft/me"),
};
