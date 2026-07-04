"use client";

import { Activity, Users, Trophy, Circle } from "lucide-react";
import { usePlayerActivity } from "@/features/activity/hooks/use-activity";
import type { ActivityItem } from "@/features/activity/api/activity-api";

function iconFor(type: string) {
  if (type.startsWith("player.team")) return Users;
  if (type.startsWith("tournament")) return Trophy;
  return Circle;
}

export function PlayerActivity({ playerId }: { playerId: string }) {
  const { data: items, isLoading } = usePlayerActivity(playerId);

  return (
    <section>
      <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
        <Activity className="h-4 w-4 text-brand-400" /> 最近の活動
      </h2>
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-12 animate-pulse rounded-lg bg-white/5" />)}
        </div>
      ) : !items || items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-white/10 py-8 text-center text-sm text-slate-500">
          活動履歴はまだありません
        </div>
      ) : (
        <ol className="relative space-y-3 border-l border-white/10 pl-5">
          {items.map((it) => <Row key={it.id} item={it} />)}
        </ol>
      )}
    </section>
  );
}

function Row({ item }: { item: ActivityItem }) {
  const Icon = iconFor(item.type);
  return (
    <li className="relative">
      <span className="absolute -left-[26px] top-0.5 flex h-5 w-5 items-center justify-center rounded-full border border-white/10 bg-slate-900">
        <Icon className="h-3 w-3 text-brand-400" />
      </span>
      <p className="text-sm text-white">{item.title}</p>
      <p className="text-xs text-slate-500">
        {new Date(item.occurred_at).toLocaleDateString("ja-JP", { year: "numeric", month: "short", day: "numeric" })}
      </p>
    </li>
  );
}
