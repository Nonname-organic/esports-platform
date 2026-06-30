"use client";

import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { notificationApi } from "../api/notification-api";

export const notificationKeys = {
  all: ["notifications"] as const,
  list: (params?: object) => [...notificationKeys.all, "list", params] as const,
  unread: () => [...notificationKeys.all, "unread"] as const,
};

export function useNotifications(params?: { unread?: boolean; search?: string; cursor?: string }) {
  return useQuery({
    queryKey: notificationKeys.list(params),
    queryFn: () => notificationApi.list(params),
    staleTime: 30 * 1000,
    placeholderData: keepPreviousData,
  });
}

export function useUnreadCount(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: notificationKeys.unread(),
    queryFn: () => notificationApi.unreadCount(),
    select: (res) => res.data.count,
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
    enabled: options?.enabled ?? true,
  });
}

export function useMarkRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => notificationApi.markRead(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
}

export function useMarkAllRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => notificationApi.markAllRead(),
    onSuccess: () => qc.invalidateQueries({ queryKey: notificationKeys.all }),
  });
}

export function useDeleteNotification() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => notificationApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: notificationKeys.all }),
  });
}
