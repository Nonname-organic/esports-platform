import { apiClient } from "@/lib/api-client";
import type { ApiResponse, ListResponse } from "@/types/tournament";

export interface LFPPost {
  id: string;
  team_id: string;
  team_name: string;
  team_tag: string;
  team_logo_url: string | null;
  owner_id: string;
  title: string;
  status: "open" | "paused" | "closed";
  roles: string[];
  headcount: number;
  min_rank: string;
  region: string;
  activity_time: string[];
  activity_level: string | null;
  tournaments: string[];
  age_requirement: string | null;
  description: string | null;
  team_intro: string | null;
  discord: string | null;
  deadline: string | null;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

export interface LFPCreateInput {
  team_id: string;
  title: string;
  status?: string;
  roles: string[];
  headcount: number;
  min_rank: string;
  region: string;
  activity_time?: string[];
  activity_level?: string;
  tournaments?: string[];
  age_requirement?: string;
  description?: string;
  team_intro?: string;
  discord?: string;
  deadline?: string;
  is_public?: boolean;
}

export interface LFPSearchParams {
  status?: string;
  region?: string;
  role?: string;
  min_rank?: string;
  limit?: number;
  offset?: number;
}

export const lfpApi = {
  list: (params?: LFPSearchParams): Promise<ListResponse<LFPPost>> => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.region) qs.set("region", params.region);
    if (params?.role) qs.set("role", params.role);
    if (params?.min_rank) qs.set("min_rank", params.min_rank);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    return apiClient.get(`/api/v1/lfp${qs.toString() ? `?${qs}` : ""}`);
  },

  mine: (): Promise<ApiResponse<LFPPost[]>> =>
    apiClient.get("/api/v1/lfp/mine"),

  get: (id: string): Promise<ApiResponse<LFPPost>> =>
    apiClient.get(`/api/v1/lfp/${id}`),

  create: (data: LFPCreateInput): Promise<ApiResponse<LFPPost>> =>
    apiClient.post("/api/v1/lfp", data),

  update: (id: string, data: Partial<LFPCreateInput>): Promise<ApiResponse<LFPPost>> =>
    apiClient.patch(`/api/v1/lfp/${id}`, data),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/api/v1/lfp/${id}`),
};
