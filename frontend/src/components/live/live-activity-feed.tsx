"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, X } from "lucide-react";
import { liveApi, type LiveActivityItem } from "@/features/live/api/live-api";
import { LiveDot } from "./live-dot";

function relTime(iso: string): string {
  const sec = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (sec < 60) return `${sec}秒前`;
  if (sec < 3600) return `${Math.floor(sec / 60)}分前`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}時間前`;
  return `${Math.floor(sec / 86400)}日前`;
}

// Backendに公開イベントがまだ無い場合の賑わい補完（リンクは張らない）。
const MOCK_FEED: LiveActivityItem[] = [
  { id: "m1", type: "player.team.joined", title: "「AXELIA」に加入しました", metadata: { actor_name: "Team AXELIA" }, occurred_at: new Date(Date.now() - 5000).toISOString() },
  { id: "m2", type: "tournament.completed", title: "「Summer Cup」が終了しました", metadata: { actor_name: "NIX" }, occurred_at: new Date(Date.now() - 12000).toISOString() },
  { id: "m3", type: "tournament.published", title: "受付を開始しました", metadata: { actor_name: "Premier Open" }, occurred_at: new Date(Date.now() - 60000).toISOString() },
];

export function LiveActivityFeed() {
  const [open, setOpen] = useState(true);

  const { data } = useQuery({
    queryKey: ["live", "activity-feed"],
    queryFn: async () => (await liveApi.feed(10)).data,
    refetchInterval: 20000,
    refetchIntervalInBackground: false, // 非表示中は停止
    staleTime: 10000,
  });

  const items = useMemo(() => {
    const src = data && data.length > 0 ? data : MOCK_FEED;
    return src.slice(0, 5);
  }, [data]);

  if (!open || items.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-40 w-72 max-w-[calc(100vw-2rem)]">
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-slate-900/95 shadow-2xl shadow-black/40 backdrop-blur">
        <div className="flex items-center justify-between border-b border-white/8 px-4 py-2.5">
          <div className="flex items-center gap-2">
            <Activity className="h-3.5 w-3.5 text-green-400" />
            <span className="text-xs font-bold tracking-wide text-white">LIVE ACTIVITY</span>
            <LiveDot />
          </div>
          <button
            onClick={() => setOpen(false)}
            className="rounded-md p-1 text-slate-500 hover:bg-white/5 hover:text-white transition-colors"
            aria-label="閉じる"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>

        <ul className="divide-y divide-white/5">
          {items.map((it) => {
            const actor = typeof it.metadata?.actor_name === "string" ? it.metadata.actor_name : undefined;
            return (
              <li key={it.id} className="animate-live-enter px-4 py-2.5">
                <div className="flex items-start gap-2.5">
                  <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-green-500/80" />
                  <div className="min-w-0 flex-1">
                    {actor && <p className="truncate text-xs font-semibold text-white">{actor}</p>}
                    <p className="truncate text-xs text-slate-400">{it.title}</p>
                    <p className="mt-0.5 text-[10px] text-slate-600">{relTime(it.occurred_at)}</p>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
