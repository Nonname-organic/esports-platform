"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, X, UserPlus, Trophy, Megaphone, Award, Star, Swords } from "lucide-react";
import { cn } from "@/lib/utils";
import { liveApi, type LiveActivityItem } from "@/features/live/api/live-api";
import { LiveDot } from "./live-dot";

function relTime(iso: string): string {
  const sec = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (sec < 60) return `${sec}秒前`;
  if (sec < 3600) return `${Math.floor(sec / 60)}分前`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}時間前`;
  return `${Math.floor(sec / 86400)}日前`;
}

// イベント種別 → アイコン + 色
function iconFor(type: string): { Icon: React.ElementType; color: string } {
  if (type.includes("mvp")) return { Icon: Star, color: "text-pink-400" };
  if (type.includes("bracket") || type.includes("match")) return { Icon: Swords, color: "text-red-400" };
  if (type.startsWith("player.team") || type.includes("registration") || type.includes("entry"))
    return { Icon: UserPlus, color: "text-brand-400" };
  if (type === "tournament.completed") return { Icon: Trophy, color: "text-yellow-400" };
  if (type.startsWith("team.achievement")) return { Icon: Award, color: "text-purple-400" };
  if (type.startsWith("tournament")) return { Icon: Megaphone, color: "text-green-400" };
  return { Icon: Activity, color: "text-slate-400" };
}

// Backendに公開イベントがまだ無い場合の賑わい補完（リンクは張らない）。
const MOCK_FEED: LiveActivityItem[] = [
  { id: "m1", type: "tournament.entry", title: "大会へ参加しました", metadata: { actor_name: "VARREL" }, occurred_at: new Date(Date.now() - 8000).toISOString() },
  { id: "m2", type: "tournament.bracket", title: "ブラケット進出", metadata: { actor_name: "ABC" }, occurred_at: new Date(Date.now() - 32000).toISOString() },
  { id: "m3", type: "match.mvp", title: "MVP獲得", metadata: { actor_name: "PlayerName" }, occurred_at: new Date(Date.now() - 120000).toISOString() },
  { id: "m4", type: "tournament.completed", title: "優勝しました", metadata: { actor_name: "XYZ" }, occurred_at: new Date(Date.now() - 2000).toISOString() },
  { id: "m5", type: "tournament.published", title: "受付開始", metadata: { actor_name: "Premier Open" }, occurred_at: new Date(Date.now() - 1000).toISOString() },
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

  // 最新到着の検知（先頭IDが変わったら数秒 NEW ハイライト）
  const [freshId, setFreshId] = useState<string | null>(null);
  const prevTop = useRef<string | null>(null);
  useEffect(() => {
    const top = items[0]?.id ?? null;
    if (top && prevTop.current && top !== prevTop.current) {
      setFreshId(top);
      const t = setTimeout(() => setFreshId(null), 4000);
      prevTop.current = top;
      return () => clearTimeout(t);
    }
    prevTop.current = top;
  }, [items]);

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
            const { Icon, color } = iconFor(it.type);
            const isFresh = it.id === freshId;
            return (
              <li
                key={it.id}
                className={cn("animate-live-enter px-4 py-2.5 transition-colors", isFresh && "bg-green-500/5")}
              >
                <div className="flex items-start gap-2.5">
                  <span className={cn("mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-lg bg-white/5", color)}>
                    <Icon className="h-3.5 w-3.5" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      {actor && <p className="truncate text-xs font-semibold text-white">{actor}</p>}
                      {isFresh && (
                        <span className="flex-shrink-0 rounded bg-green-500/20 px-1 text-[9px] font-black tracking-wide text-green-400 animate-glow-pulse">
                          NEW
                        </span>
                      )}
                    </div>
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
