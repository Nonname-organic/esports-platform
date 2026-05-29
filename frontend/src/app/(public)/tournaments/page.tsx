"use client";

// CSR: TanStack Query で無限スクロール + クライアントサイドフィルタリング
// staleTime: 5分 → ISR revalidate: 300 相当のキャッシュ戦略

import { useRef, useCallback } from "react";
import { useState } from "react";
import { Filter } from "lucide-react";
import { TournamentCard } from "@/features/tournaments/components/tournament-card";
import { useTournaments } from "@/features/tournaments/hooks/use-tournaments";
import type { GameType, TournamentStatus } from "@/types/tournament";
import { cn } from "@/lib/utils";

const GAMES: Array<{ value: GameType | "ALL"; label: string }> = [
  { value: "ALL", label: "すべて" },
  { value: "VALORANT", label: "VALORANT" },
  { value: "LOL", label: "LoL" },
  { value: "APEX", label: "APEX" },
  { value: "CS2", label: "CS2" },
  { value: "OVERWATCH", label: "OW2" },
];

const STATUSES: Array<{ value: TournamentStatus | "ALL"; label: string }> = [
  { value: "ALL", label: "すべて" },
  { value: "registration_open", label: "受付中" },
  { value: "ongoing", label: "開催中" },
  { value: "completed", label: "終了済み" },
];

export default function TournamentsPage() {
  const [game, setGame] = useState<GameType | undefined>();
  const [status, setStatus] = useState<TournamentStatus | undefined>();

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading } =
    useTournaments({ game, status });

  // Intersection Observer による無限スクロール
  const observer = useRef<IntersectionObserver | null>(null);
  const sentinelRef = useCallback(
    (node: HTMLDivElement | null) => {
      if (isFetchingNextPage) return;
      observer.current?.disconnect();
      if (!node) return;
      observer.current = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && hasNextPage) fetchNextPage();
      });
      observer.current.observe(node);
    },
    [isFetchingNextPage, hasNextPage, fetchNextPage],
  );

  const tournaments = data?.pages.flatMap((p) => p.data) ?? [];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* ページヘッダー */}
      <div className="mb-8">
        <h1 className="text-3xl font-black text-white">大会一覧</h1>
        <p className="mt-1 text-slate-400">参加・観戦できる e-スポーツ大会を探す</p>
      </div>

      {/* フィルター: ゲーム */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row">
        <div className="flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 p-1">
          {GAMES.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setGame(value === "ALL" ? undefined : value)}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                (value === "ALL" ? !game : game === value)
                  ? "bg-brand-500 text-white"
                  : "text-slate-400 hover:text-white",
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {/* フィルター: ステータス */}
        <div className="flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 p-1">
          {STATUSES.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setStatus(value === "ALL" ? undefined : value)}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                (value === "ALL" ? !status : status === value)
                  ? "bg-brand-500 text-white"
                  : "text-slate-400 hover:text-white",
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* 一覧グリッド */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-64 animate-pulse rounded-xl bg-white/5" />
          ))}
        </div>
      ) : tournaments.length === 0 ? (
        <div className="py-24 text-center">
          <Filter className="mx-auto mb-4 h-12 w-12 text-slate-600" />
          <p className="text-slate-400">条件に合う大会はありません</p>
          <button
            onClick={() => { setGame(undefined); setStatus(undefined); }}
            className="mt-3 text-sm text-brand-400 hover:text-brand-300"
          >
            フィルターをリセット
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {tournaments.map((t) => (
            <TournamentCard key={t.id} tournament={t} />
          ))}
        </div>
      )}

      {/* 無限スクロール sentinel */}
      <div ref={sentinelRef} className="mt-8 flex h-10 items-center justify-center">
        {isFetchingNextPage && (
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
        )}
      </div>
    </div>
  );
}
