import { apiClient } from "@/lib/api-client";
import type { AdminDashboard, AdminNotification } from "@/types/admin";

interface ApiResponse<T> { data: T }

export const adminApi = {
  getDashboard: (): Promise<ApiResponse<AdminDashboard>> =>
    apiClient.get("/api/v1/admin/dashboard"),

  getNotifications: (): Promise<{ data: AdminNotification[] }> =>
    apiClient.get("/api/v1/admin/notifications"),

  markNotificationRead: (id: string): Promise<void> =>
    apiClient.patch(`/api/v1/admin/notifications/${id}/read`),

  markAllRead: (): Promise<void> =>
    apiClient.patch("/api/v1/admin/notifications/read-all"),
};
