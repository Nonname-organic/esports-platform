"use client";

import { useState } from "react";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { ja } from "date-fns/locale";
import {
  Bell, Check, CheckCheck, Trash2, Search, Filter,
  Trophy, Users, Swords, AlertCircle, Calendar, BarChart2, Info,
} from "lucide-react";
import {
  useNotifications, useMarkRead, useMarkAllRead, useDeleteNotification,
} from "@/features/notifications/hooks/use-notifications";
import { cn } from "@/lib/utils";
import type { NotificationItem } from "@/features/notifications/api/notification-api";

// 通知種別 → アイコン/色
const TYPE_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  tournament_invite: { icon: Trophy, color: "text-brand-400", bg: "bg-brand-500/10" },
  team_invite: { icon: Users, color: "text-purple-400", bg: "bg-purple-500/10" },
  application_approved: { icon: Check, color: "text-green-400", bg: "bg-green-500/10" },
  registration_approved: { icon: Check, color: "text-green-400", bg: "bg-green-500/10" },
  application_rejected: { icon: AlertCircle, color: "text-red-400", bg: "bg-red-500/10" },
  registration_rejected: { icon: AlertCircle, color: "text-red-400", bg: "bg-red-500/10" },
  match_reminder: { icon: Calendar, color: "text-yellow-400", bg: "bg-yellow-500/10" },
  match_scheduled: { icon: Calendar, color: "text-yellow-400", bg: "bg-yellow-500/10" },
  checkin_reminder: { icon: Calendar, color: "text-blue-400", bg: "bg-blue-500/10" },
  check_in_reminder: { icon: Calendar, color: "text-blue-400", bg: "bg-blue-500/10" },
  result_updated: { icon: Swords, color: "text-cyan-400", bg: "bg-cyan-500/10" },
  match_result: { icon: Swords, color: "text-cyan-400", bg: "bg-cyan-500/10" },
  ranking_updated: { icon: BarChart2, color: "text-orange-400", bg: "bg-orange-500/10" },
  general: { icon: Info, color: "text-slate-400", bg: "bg-slate-500/10" },
};

const FILTERS = [
  { value: "all", label: "すべて" },
  { value: "unread", label: "未読" },
];

export default function NotificationsPage() {
  const [filter, setFilter] = useState<"all" | "unread">("all");
  const [search, setSearch] = useState("");

  const { data, isLoading } = useNotifications({
    unread: filter === "unread",
    search: search || undefined,
  });
  const markRead = useMarkRead();
  const markAllRead = useMarkAllRead();
  const deleteNotif = useDeleteNotification();

  const notifications = data?.data ?? [];
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      {/* ヘッダー */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-2xl bg-brand-500/10 p-2.5">
            <Bell className="h-6 w-6 text-brand-400" />
          </div>
          <div>
            <h1 className="text-xl font-black text-white">通知センター</h1>
            <p className="text-sm text-slate-500">
              {unreadCount > 0 ? `未読 ${unreadCount}件` : "すべて既読"}
            </p>
          </div>
        </div>
        {unreadCount > 0 && (
          <button
            onClick={() => markAllRead.mutate()}
            disabled={markAllRead.isPending}
            className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-400 hover:text-white transition-colors disabled:opacity-50"
          >
            <CheckCheck className="h-4 w-4" />
            すべて既読
          </button>
        )}
      </div>

      {/* フィルター + 検索 */}
      <div className="mb-5 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="通知を検索..."
            className="w-full rounded-xl border border-white/10 bg-slate-900 py-2.5 pl-9 pr-4 text-sm text-white placeholder-slate-600 outline-none focus:border-brand-500"
          />
        </div>
        <div className="flex gap-1 rounded-xl border border-white/10 bg-slate-900 p-1">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value as "all" | "unread")}
              className={cn(
                "rounded-lg px-4 py-1.5 text-xs font-semibold transition-colors",
                filter === f.value ? "bg-brand-500 text-white" : "text-slate-500 hover:text-white",
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* 通知リスト */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-white/5" />
          ))}
        </div>
      ) : notifications.length === 0 ? (
        <div className="flex flex-col items-center py-20 text-center">
          <Bell className="mb-4 h-12 w-12 text-slate-700" />
          <p className="font-semibold text-white">通知はありません</p>
          <p className="mt-1 text-sm text-slate-400">
            {filter === "unread" ? "未読の通知はありません" : "新しい通知が届くとここに表示されます"}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {notifications.map((n) => (
            <NotificationCard
              key={n.id}
              notification={n}
              onRead={() => markRead.mutate(n.id)}
              onDelete={() => deleteNotif.mutate(n.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function NotificationCard({
  notification, onRead, onDelete,
}: {
  notification: NotificationItem;
  onRead: () => void;
  onDelete: () => void;
}) {
  const cfg = TYPE_CONFIG[notification.type] ?? TYPE_CONFIG.general;
  const Icon = cfg.icon;

  const timeAgo = (() => {
    try {
      return formatDistanceToNow(new Date(notification.created_at), { addSuffix: true, locale: ja });
    } catch {
      return "";
    }
  })();

  const content = (
    <div
      className={cn(
        "flex items-start gap-3 rounded-xl border p-4 transition-colors",
        notification.is_read
          ? "border-white/5 bg-transparent"
          : "border-brand-500/20 bg-slate-900",
      )}
    >
      <div className={cn("mt-0.5 flex-shrink-0 rounded-lg p-2", cfg.bg)}>
        <Icon className={cn("h-4 w-4", cfg.color)} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p className={cn("text-sm font-semibold", notification.is_read ? "text-slate-400" : "text-white")}>
            {notification.title}
          </p>
          {!notification.is_read && <span className="mt-1 h-2 w-2 flex-shrink-0 rounded-full bg-brand-500" />}
        </div>
        {notification.body && (
          <p className="mt-0.5 text-xs text-slate-500 line-clamp-2">{notification.body}</p>
        )}
        <p className="mt-1 text-[10px] text-slate-600">{timeAgo}</p>
      </div>

      <div className="flex flex-shrink-0 items-center gap-1">
        {!notification.is_read && (
          <button
            onClick={(e) => { e.preventDefault(); onRead(); }}
            className="rounded p-1.5 text-slate-600 hover:text-brand-400 transition-colors"
            title="既読にする"
          >
            <Check className="h-3.5 w-3.5" />
          </button>
        )}
        <button
          onClick={(e) => { e.preventDefault(); onDelete(); }}
          className="rounded p-1.5 text-slate-600 hover:text-red-400 transition-colors"
          title="削除"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );

  if (notification.action_url) {
    return (
      <Link href={notification.action_url} onClick={() => !notification.is_read && onRead()}>
        {content}
      </Link>
    );
  }
  return content;
}
