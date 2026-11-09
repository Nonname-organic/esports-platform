"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi, type AdminUserItem } from "../api/admin-api";

export const adminKeys = {
  all: ["admin"] as const,
  dashboard: () => [...adminKeys.all, "dashboard"] as const,
  notifications: () => [...adminKeys.all, "notifications"] as const,
  users: (q: string) => [...adminKeys.all, "users", q] as const,
};

export function useAdminUsers(q: string) {
  return useQuery({
    queryKey: adminKeys.users(q),
    queryFn: () => adminApi.listUsers(q),
    select: (res) => res.data,
  });
}

export function useUpdateAdminUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; is_active?: boolean; role?: AdminUserItem["role"] }) =>
      adminApi.updateUser(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: [...adminKeys.all, "users"] }),
  });
}

export function useAdminDashboard() {
  return useQuery({
    queryKey: adminKeys.dashboard(),
    queryFn: () => adminApi.getDashboard(),
    select: (res) => res.data,
    staleTime: 2 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });
}

export function useAdminNotifications() {
  return useQuery({
    queryKey: adminKeys.notifications(),
    queryFn: () => adminApi.getNotifications(),
    select: (res) => res.data,
    staleTime: 60 * 1000,
    refetchInterval: 2 * 60 * 1000,
  });
}

export function useMarkNotificationRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminApi.markNotificationRead(id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: adminKeys.notifications() }),
  });
}

export function useMarkAllRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => adminApi.markAllRead(),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: adminKeys.notifications() }),
  });
}
