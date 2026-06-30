"use client";

import Link from "next/link";
import { Bell } from "lucide-react";
import { useUnreadCount } from "@/features/notifications/hooks/use-notifications";
import { useAuthStore } from "@/store/auth-store";

export function NotificationBell() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const { data: unreadCount } = useUnreadCount({ enabled: isAuthenticated });

  if (!isAuthenticated) return null;

  return (
    <Link
      href="/notifications"
      className="relative rounded-lg p-2 text-slate-400 hover:bg-white/5 hover:text-white transition-colors"
      aria-label="通知"
    >
      <Bell className="h-5 w-5" />
      {unreadCount != null && unreadCount > 0 && (
        <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-black text-white">
          {unreadCount > 99 ? "99+" : unreadCount}
        </span>
      )}
    </Link>
  );
}
