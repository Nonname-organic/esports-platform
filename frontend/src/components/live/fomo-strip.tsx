"use client";

import { useQuery } from "@tanstack/react-query";
import { Flame, Eye } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { ListResponse, TournamentSummary } from "@/types/tournament";
import { useLive } from "@/features/live/provider/live-provider";
import { AnimatedNumber } from "./animated-number";
import { LiveDot } from "./live-dot";

function hoursUntil(iso: string | null): number | null {
  if (!iso) return null;
  const ms = new Date(iso).getTime() - Date.now();
  if (Number.isNaN(ms) || ms <= 0) return null;
  return Math.max(1, Math.floor(ms / 3600000));
}

/** FOMO（参加しないと損）を煽るリアルタイム・チップ群。値は LiveProvider + 受付一覧から。 */
export function FomoStrip() {
  const { live } = useLive();
  const { data } = useQuery({
    queryKey: ["live", "entry-open"], // FeaturedEntry / EntryOpen と共有
    queryFn: async () => {
      const res = await apiClient.get<ListResponse<TournamentSummary>>(
        "/api/v1/tournaments?status=registration_open&limit=12",
      );
      return res.data;
    },
    refetchInterval: 60000,
    refetchIntervalInBackground: false,
    staleTime: 30000,
  });

  const soonest = (data ?? [])
    .slice()
    .sort((a, b) => {
      const ta = a.registration_end_at ? new Date(a.registration_end_at).getTime() : Infinity;
      const tb = b.registration_end_at ? new Date(b.registration_end_at).getTime() : Infinity;
      return ta - tb;
    })[0];

  const slotsLeft = soonest ? Math.max(0, soonest.max_teams - soonest.registered_teams) : null;
  const hrs = hoursUntil(soonest?.registration_end_at ?? null);

  const chips: { key: string; icon: "fire" | "eye"; node: React.ReactNode; hot?: boolean }[] = [];
  if ((live?.entries_today ?? 0) > 0)
    chips.push({ key: "today", icon: "fire", node: <>今日 <Num v={live!.entries_today!} /> チームが参加</> });
  if (slotsLeft != null)
    chips.push({ key: "slots", icon: "fire", hot: slotsLeft <= 32, node: <>あと <Num v={slotsLeft} /> 枠</> });
  if ((live?.online_participants ?? 0) > 0)
    chips.push({ key: "view", icon: "eye", node: <>現在 <Num v={live!.online_participants} /> 人が閲覧中</> });
  if (hrs != null)
    chips.push({ key: "deadline", icon: "fire", hot: hrs <= 24, node: <>締切まで <Num v={hrs} /> 時間</> });
  if ((live?.entries_recent ?? 0) > 0)
    chips.push({ key: "recent", icon: "fire", hot: true, node: <>直近5分で <Num v={live!.entries_recent!} /> チーム参加</> });

  if (chips.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {chips.map((c) => (
        <span
          key={c.key}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-bold",
            c.hot
              ? "border-red-500/40 bg-red-500/10 text-red-300 animate-glow-pulse"
              : "border-white/10 bg-white/[0.03] text-slate-300",
          )}
        >
          {c.icon === "fire" ? (
            <Flame className={cn("h-3.5 w-3.5", c.hot ? "text-red-400" : "text-orange-400")} />
          ) : (
            <span className="inline-flex items-center gap-1"><LiveDot /><Eye className="h-3.5 w-3.5 text-cyan-400" /></span>
          )}
          {c.node}
        </span>
      ))}
    </div>
  );
}

function Num({ v }: { v: number }) {
  return <span className="font-black text-white"><AnimatedNumber value={v} durationMs={700} /></span>;
}
