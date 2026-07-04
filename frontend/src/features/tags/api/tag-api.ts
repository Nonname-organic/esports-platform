import { apiClient } from "@/lib/api-client";
import type { ApiResponse } from "@/types/tournament";

export interface Tag {
  id: string;
  slug: string;
  label: string;
  category: string | null;
  color: string | null;
}

export type TagEntityType = "team" | "tournament" | "lfp" | "lft";

export const tagApi = {
  catalog: (params?: { category?: string; q?: string }): Promise<ApiResponse<Tag[]>> => {
    const qs = new URLSearchParams();
    if (params?.category) qs.set("category", params.category);
    if (params?.q) qs.set("q", params.q);
    const q = qs.toString();
    return apiClient.get(`/api/v1/tags${q ? `?${q}` : ""}`);
  },

  forEntity: (entityType: TagEntityType, entityId: string): Promise<ApiResponse<Tag[]>> =>
    apiClient.get(`/api/v1/tags/of/${entityType}/${entityId}`),

  setForEntity: (entityType: TagEntityType, entityId: string, tags: string[]): Promise<ApiResponse<Tag[]>> =>
    apiClient.put(`/api/v1/tags/of/${entityType}/${entityId}`, { tags }),
};
