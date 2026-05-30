"use client";

import { formatDistanceToNow } from "date-fns";
import { ja } from "date-fns/locale";
import {
  Trophy, CheckCircle2, XCircle, Users, Swords, UserPlus, ClipboardCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { Activity, ActivityType } from "@/types/admin";

const ACTIVITY_CONFIG: Record<
  ActivityType,
  { icon: React.ElementType; iconBg: string; iconColor: string; label: string }
> = {
  tournament_created: {
    icon: Trophy,
    iconBg: "bg-brand-500/10",
    iconColor: "text-brand-400",
    label: "大会作成",
  },
  tournament_completed: {
    icon: CheckCircle2,
    iconBg: "bg-green-500/10",
    iconColor: "text-green-400",
    label: "大会終了",
  },
  tournament_cancelled: {
    icon: XCircle,
    iconBg: "bg-red-500/10",
    iconColor: "text-red-400",
    label: "大会中止",
  },
  team_registered: {
    icon: Users,
    iconBg: "bg-purple-500/10",
    iconColor: "text-purple-400",
    label: "チーム登録",
  },
  match_completed: {
    icon: Swords,
    iconBg: "bg-cyan-500/10",
    iconColor: "text-cyan-400",
    label: "試合終了",
  },
  result_submitted: {
    icon: ClipboardCheck,
    iconBg: "bg-yellow-500/10",
    iconColor: "text-yellow-400",
    label: "結果報告",
  },
  user_joined: {
    icon: UserPlus,
    iconBg: "bg-green-500/10",
    iconColor: "text-green-400",
    label: "ユーザー参加",
  },
};

interface ActivityItemProps {
  activity: Activity;
}

function ActivityItem({ activity }: ActivityItemProps) {
  const cfg = ACTIVITY_CONFIG[activity.type];

  const timeAgo = (() => {
    try {
      return formatDistanceToNow(new Date(activity.created_at), {
        addSuffix: true,
        locale: ja,
      });
    } catch {
      return "—";
    }
  })();

  return (
    <div className="flex items-start gap-3 py-3">
      <div className={cn("mt-0.5 flex-shrink-0 rounded-lg p-1.5", cfg.iconBg)}>
        <cfg.icon className={cn("h-3.5 w-3.5", cfg.iconColor)} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white">{activity.title}</p>
        <p className="mt-0.5 text-xs text-slate-500 line-clamp-1">{activity.description}</p>
        <div className="mt-1 flex items-center gap-2 text-[10px] text-slate-600">
          <span className={cn("rounded-full border px-1.5 py-0.5 text-[9px] font-semibold", cfg.iconBg, cfg.iconColor)}>
            {cfg.label}
          </span>
          <span>{timeAgo}</span>
        </div>
      </div>
    </div>
  );
}

interface ActivityFeedProps {
  activities: Activity[];
}

export function ActivityFeed({ activities }: ActivityFeedProps) {
  return (
    <section className="rounded-xl border border-white/10 bg-slate-900">
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
        <div>
          <h2 className="text-sm font-bold text-white">最近のアクティビティ</h2>
          <p className="text-xs text-slate-500">{activities.length}件</p>
        </div>
      </div>

      <div className="max-h-96 divide-y divide-white/5 overflow-y-auto px-5 scrollbar-thin">
        {activities.length === 0 ? (
          <div className="flex h-32 items-center justify-center">
            <p className="text-sm text-slate-500">アクティビティがありません</p>
          </div>
        ) : (
          activities.map((a) => <ActivityItem key={a.id} activity={a} />)
        )}
      </div>
    </section>
  );
}
