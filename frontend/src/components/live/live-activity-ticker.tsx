"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { liveApi, type LiveActivityItem } from "@/features/live/api/live-api";
import { activityMeta } from "@/features/live/lib/activity-meta";
import { LiveDot } from "./live-dot";

function relTime(iso: string): string {
  const sec = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (sec < 5) return "今";
  if (sec < 60) return `${sec}秒前`;
  if (sec < 3600) return `${Math.floor(sec / 60)}分前`;
  return `${Math.floor(sec / 3600)}時間前`;
}

const MOCK: LiveActivityItem[] = [
  { id: "t1", type: "tournament.entry", title: "大会へ参加しました", metadata: { actor_name: "VARREL" }, occurred_at: new Date(Date.now() - 8000).toISOString() },
  { id: "t2", type: "tournament.bracket", title: "ブラケット進出", metadata: { actor_name: "ABC" }, occurred_at: new Date(Date.now() - 32000).toISOString() },
  { id: "t3", type: "match.mvp", title: "MVP獲得", metadata: { actor_name: "Player" }, occurred_at: new Date(Date.now() - 120000).toISOString() },
  { id: "t4", type: "tournament.completed", title: "優勝しました", metadata: { actor_name: "XYZ" }, occurred_at: new Date(Date.now() - 1500).toISOString() },
  { id: "t5", type: "tournament.published", title: "受付開始", metadata: { actor_name: "Premier Open" }, occurred_at: new Date(Date.now() - 1000).toISOString() },
];

/** Hero 近くの横型リアルタイム・ティッカー（右下フィードとは別に常時視界へ）。 */
export function LiveActivityTicker() {
  const { data } = useQuery({
    queryKey: ["live", "activity-feed"], // 右下フィードとキャッシュ共有
    queryFn: async () => (await liveApi.feed(10)).data,
    refetchInterval: 20000,
    refetchIntervalInBackground: false,
    staleTime: 10000,
  });

  const items = useMemo(() => {
    const src = data && data.length > 0 ? data : MOCK;
    return src.slice(0, 6);
  }, [data]);

  if (items.length === 0) return null;

  return (
    <div className="flex items-center gap-3 overflow-hidden rounded-full border border-white/10 bg-slate-900/60 px-4 py-2 backdrop-blur">
      <span className="flex flex-shrink-0 items-center gap-1.5">
        <LiveDot />
        <span className="text-[11px] font-black tracking-widest text-green-400">LIVE FEED</span>
      </span>
      <div className="flex min-w-0 flex-1 items-center gap-4 overflow-x-auto scrollbar-thin">
        {items.map((it) => {
          const actor = typeof it.metadata?.actor_name === "string" ? it.metadata.actor_name : undefined;
          const m = activityMeta(it.type);
          return (
            <span key={it.id} className="flex flex-shrink-0 items-center gap-1.5 whitespace-nowrap text-xs">
              <m.Icon className={cn("h-3.5 w-3.5", m.color)} />
              {m.label && <span className={cn("rounded px-1 text-[9px] font-black tracking-wider", m.bg, m.color)}>{m.label}</span>}
              {actor && <span className="font-semibold text-white">{actor}</span>}
              <span className="text-slate-400">{it.title}</span>
              <span className="text-slate-600">· {relTime(it.occurred_at)}</span>
            </span>
          );
        })}
      </div>
    </div>
  );
}
