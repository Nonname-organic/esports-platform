"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Users, Trophy, Clock, Coins, Eye, PlayCircle, Timer } from "lucide-react";
import { cn, getGameColor, formatPrize } from "@/lib/utils";
import type { TournamentSummary } from "@/types/tournament";
import { deadlineLabel } from "@/features/live/lib/format";
import { LiveBadge } from "./live-dot";

type Mode = "entry" | "live";

// 閲覧人数（モック許可枠）: props から決定的に算出（SSR/CSR一致・hydration safe）。
function viewerEstimate(t: TournamentSummary): number {
  return 120 + ((t.registered_teams * 53 + t.name.length * 17) % 900);
}
function elapsedLabel(startIso: string | null): string {
  if (!startIso) return "進行中";
  const ms = Date.now() - new Date(startIso).getTime();
  if (Number.isNaN(ms)) return "進行中";
  if (ms < 0) return "まもなく開始";
  const h = Math.floor(ms / 3600000);
  if (h >= 1) return `開始${h}時間経過`;
  return `開始${Math.max(1, Math.floor(ms / 60000))}分経過`;
}

/** 開催中(LIVE) / 受付中(ENTRY OPEN) 共通の大会カード。状態バッジ・締切・賞金・参加率を強調。 */
export function TournamentLiveCard({ t, mode }: { t: TournamentSummary; mode: Mode }) {
  const fill = Math.min((t.registered_teams / Math.max(t.max_teams, 1)) * 100, 100);
  const dl = mode === "entry" ? deadlineLabel(t.registration_end_at) : null;
  const isLive = mode === "live";

  // 経過時間は時刻依存 → mount後のみ描画（hydration mismatch回避 / 行は常設でCLSなし）
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const accent = isLive
    ? "hover:border-red-500/60 hover:shadow-[0_16px_50px_-12px_rgba(239,68,68,0.5)]"
    : "hover:border-green-500/60 hover:shadow-[0_16px_50px_-12px_rgba(34,197,94,0.45)]";

  return (
    <Link
      href={`/tournaments/${t.id}`}
      className={cn(
        "group relative block overflow-hidden rounded-2xl border border-white/10 bg-slate-900",
        "transition-all duration-300 will-change-transform hover:-translate-y-1 hover:rotate-[0.5deg]",
        accent,
      )}
    >
      {/* バナー（アイドルでゆっくりZoom） */}
      <div className="relative h-36 overflow-hidden bg-gradient-to-br from-slate-800 to-slate-950">
        {t.banner_url ? (
          <img
            src={t.banner_url}
            alt=""
            className="h-full w-full object-cover opacity-55 animate-slow-zoom transition-opacity duration-500 group-hover:opacity-80"
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <Trophy className="h-12 w-12 text-white/10" />
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-slate-900/30 to-transparent" />

        {/* ゲーム + 状態バッジ */}
        <span className={cn("absolute left-3 top-3 rounded-full border px-2.5 py-0.5 text-[11px] font-bold", getGameColor(t.game))}>
          {t.game}
        </span>
        <span className="absolute right-3 top-3">
          {mode === "entry" ? (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-green-500/40 bg-green-500/15 px-2 py-0.5 text-[11px] font-black tracking-wide text-green-400">
              <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-live-blink" />
              ENTRY OPEN
            </span>
          ) : (
            <LiveBadge />
          )}
        </span>

        {/* 締切 or 経過時間 */}
        {dl ? (
          <span className={cn(
            "absolute bottom-3 left-3 inline-flex items-center gap-1 rounded-lg bg-black/55 px-2 py-1 text-xs font-bold backdrop-blur-sm",
            dl.urgent ? "text-red-400" : "text-yellow-400",
          )}>
            <Clock className="h-3.5 w-3.5" /> {dl.text}
          </span>
        ) : isLive ? (
          <span className="absolute bottom-3 left-3 inline-flex items-center gap-1 rounded-lg bg-black/55 px-2 py-1 text-xs font-bold text-slate-200 backdrop-blur-sm">
            <Timer className="h-3.5 w-3.5" /> {mounted ? elapsedLabel(t.start_at) : "進行中"}
          </span>
        ) : null}

        {/* 賞金（Prize Shine） */}
        {t.prize_pool != null && t.prize_pool > 0 && (
          <span className="absolute bottom-3 right-3 inline-flex items-center gap-1 overflow-hidden rounded-lg bg-black/55 px-2 py-1 text-xs font-bold text-yellow-400 backdrop-blur-sm">
            <span className="pointer-events-none absolute inset-y-0 -left-1/2 w-1/2 bg-gradient-to-r from-transparent via-yellow-100/40 to-transparent animate-shine" />
            <Coins className="relative h-3.5 w-3.5" /> <span className="relative">{formatPrize(t.prize_pool)}</span>
          </span>
        )}
      </div>

      {/* 本文 */}
      <div className="p-4">
        <h3 className="line-clamp-1 font-bold text-white">{t.name}</h3>
        <div className="mt-2 flex items-center gap-2 text-sm text-slate-400">
          <Users className="h-3.5 w-3.5 text-slate-500" />
          <span className="font-semibold text-white">{t.registered_teams}</span>
          <span className="text-slate-500">/ {t.max_teams} Teams</span>
          {isLive && (
            <span className="ml-auto inline-flex items-center gap-1 text-xs text-slate-400">
              <Eye className="h-3.5 w-3.5 text-red-400" />
              <span className="font-semibold text-white tabular-nums">{viewerEstimate(t).toLocaleString()}</span>
              観戦中
            </span>
          )}
        </div>

        <div className="mt-3">
          <div className="mb-1 flex items-center justify-between text-[11px] text-slate-500">
            <span>{mode === "entry" ? "エントリー状況" : "参加状況"}</span>
            <span className="tabular-nums">{fill.toFixed(0)}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500",
                isLive ? "bg-gradient-to-r from-brand-500 to-red-400" : "bg-gradient-to-r from-green-500 to-emerald-400",
              )}
              style={{ width: `${fill}%` }}
            />
          </div>
        </div>

        {isLive && (
          <span className="mt-3 inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-red-500/15 px-3 py-2 text-sm font-bold text-red-300 transition-colors group-hover:bg-red-500/25">
            <PlayCircle className="h-4 w-4" /> 観戦する
          </span>
        )}
      </div>
    </Link>
  );
}
