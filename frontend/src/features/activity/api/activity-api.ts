import { apiClient } from "@/lib/api-client";
import type { ApiResponse } from "@/types/tournament";

export interface ActivityItem {
  id: string;
  type: string;
  title: string;
  metadata: Record<string, unknown>;
  occurred_at: string;
}

export const activityApi = {
  playerActivity: (playerId: string, params?: { limit?: number; offset?: number }): Promise<ApiResponse<ActivityItem[]>> => {
    const qs = new URLSearchParams();
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    const q = qs.toString();
    return apiClient.get(`/api/v1/players/${playerId}/activity${q ? `?${q}` : ""}`);
  },
};
