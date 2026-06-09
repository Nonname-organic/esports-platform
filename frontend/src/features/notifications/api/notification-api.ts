import { apiClient } from "@/lib/api-client";
import type { ApiResponse, ListResponse } from "@/types/tournament";

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  body: string | null;
  is_read: boolean;
  action_url: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export const notificationApi = {
  list: (params?: { unread?: boolean; search?: string; cursor?: string; limit?: number }): Promise<ListResponse<NotificationItem>> => {
    const qs = new URLSearchParams();
    if (params?.unread) qs.set("unread", "true");
    if (params?.search) qs.set("search", params.search);
    if (params?.cursor) qs.set("cursor", params.cursor);
    if (params?.limit) qs.set("limit", String(params.limit));
    const q = qs.toString();
    return apiClient.get(`/api/v1/notifications${q ? `?${q}` : ""}`);
  },

  unreadCount: (): Promise<ApiResponse<{ count: number }>> =>
    apiClient.get("/api/v1/notifications/unread-count"),

  markRead: (id: string): Promise<void> =>
    apiClient.patch(`/api/v1/notifications/${id}/read`),

  markAllRead: (): Promise<void> =>
    apiClient.patch("/api/v1/notifications/read-all"),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/api/v1/notifications/${id}`),
};
