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

  listUsers: (q: string): Promise<ApiResponse<AdminUserItem[]>> =>
    apiClient.get(`/api/v1/admin/users${q ? `?q=${encodeURIComponent(q)}` : ""}`),

  updateUser: (
    id: string,
    body: { is_active?: boolean; role?: AdminUserItem["role"] },
  ): Promise<ApiResponse<AdminUserItem>> =>
    apiClient.patch(`/api/v1/admin/users/${id}`, body),
};

export interface AdminUserItem {
  id: string;
  username: string;
  email: string;
  role: "admin" | "organizer" | "team_manager" | "player" | "viewer";
  is_active: boolean;
  created_at: string | null;
}
