"use client";

import { formatDistanceToNow } from "date-fns";
import { ja } from "date-fns/locale";
import { Bell, CheckCheck, AlertTriangle, Info, CheckCircle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  useAdminNotifications,
  useMarkNotificationRead,
  useMarkAllRead,
} from "@/features/admin/hooks/use-admin";
import type { AdminNotification, NotificationType } from "@/types/admin";

const TYPE_CONFIG: Record<NotificationType, {
  icon: React.ElementType;
  iconBg: string;
  iconColor: string;
  borderColor: string;
}> = {
  warning: {
    icon: AlertTriangle,
    iconBg: "bg-yellow-500/10",
    iconColor: "text-yellow-400",
    borderColor: "border-yellow-500/20",
  },
  error: {
    icon: XCircle,
    iconBg: "bg-red-500/10",
    iconColor: "text-red-400",
    borderColor: "border-red-500/20",
  },
  success: {
    icon: CheckCircle,
    iconBg: "bg-green-500/10",
    iconColor: "text-green-400",
    borderColor: "border-green-500/20",
  },
  info: {
    icon: Info,
    iconBg: "bg-brand-500/10",
    iconColor: "text-brand-400",
    borderColor: "border-brand-500/20",
  },
};

function NotificationItem({ notification }: { notification: AdminNotification }) {
  const cfg = TYPE_CONFIG[notification.type];
  const markRead = useMarkNotificationRead();

  const timeAgo = (() => {
    try {
      return formatDistanceToNow(new Date(notification.created_at), {
        addSuffix: true,
        locale: ja,
      });
    } catch {
      return "—";
    }
  })();

  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border p-3 transition-colors",
        notification.is_read
          ? "border-white/5 bg-transparent opacity-50"
          : cn("border", cfg.borderColor, "bg-slate-800/50"),
      )}
    >
      <div className={cn("mt-0.5 flex-shrink-0 rounded-lg p-1.5", cfg.iconBg)}>
        <cfg.icon className={cn("h-3.5 w-3.5", cfg.iconColor)} />
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white">{notification.title}</p>
        <p className="mt-0.5 text-xs text-slate-400 leading-relaxed">{notification.message}</p>
        <div className="mt-1.5 flex items-center gap-2">
          <span className="text-[10px] text-slate-600">{timeAgo}</span>
          {notification.action_url && (
            <a
              href={notification.action_url}
              className="text-[10px] font-semibold text-brand-400 hover:text-brand-300 transition-colors"
            >
              詳細を見る →
            </a>
          )}
        </div>
      </div>

      {!notification.is_read && (
        <button
          onClick={() => markRead.mutate(notification.id)}
          disabled={markRead.isPending}
          className="flex-shrink-0 rounded p-1 text-slate-600 hover:text-white transition-colors"
          title="既読にする"
        >
          <CheckCheck className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}

export function NotificationPanel() {
  const { data: notifications, isLoading } = useAdminNotifications();
  const markAll = useMarkAllRead();

  const unreadCount = notifications?.filter((n) => !n.is_read).length ?? 0;
  const sorted = [...(notifications ?? [])].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  return (
    <section className="rounded-xl border border-white/10 bg-slate-900">
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
        <div className="flex items-center gap-2">
          <div className="relative">
            <div className="rounded-lg bg-yellow-500/10 p-1.5">
              <Bell className="h-4 w-4 text-yellow-400" />
            </div>
            {unreadCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[9px] font-black text-white">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">通知</h2>
            <p className="text-xs text-slate-500">
              {unreadCount > 0 ? `未読 ${unreadCount}件` : "すべて既読"}
            </p>
          </div>
        </div>

        {unreadCount > 0 && (
          <button
            onClick={() => markAll.mutate()}
            disabled={markAll.isPending}
            className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:text-white transition-colors disabled:opacity-50"
          >
            <CheckCheck className="h-3.5 w-3.5" />
            すべて既読
          </button>
        )}
      </div>

      <div className="max-h-96 space-y-2 overflow-y-auto p-4 scrollbar-thin">
        {isLoading && (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-16 animate-pulse rounded-lg bg-white/5" />
            ))}
          </div>
        )}

        {!isLoading && sorted.length === 0 && (
          <div className="flex h-32 items-center justify-center">
            <div className="text-center">
              <Bell className="mx-auto mb-2 h-8 w-8 text-slate-700" />
              <p className="text-sm text-slate-500">通知はありません</p>
            </div>
          </div>
        )}

        {!isLoading &&
          sorted.map((n) => <NotificationItem key={n.id} notification={n} />)}
      </div>
    </section>
  );
}
