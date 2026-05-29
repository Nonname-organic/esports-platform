"use client";

// CSR + WebSocket:
// 試合スコアはリアルタイム更新が必要なため、完全 CSR + WebSocket 購読
// queryKey は useMatchWebSocket と揃えて ["matches", "detail", id] にする

import { use, useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ChevronRight, Wifi, WifiOff } from "lucide-react";
import { matchApi } from "@/features/matches/api/match-api";
import { MatchScore } from "@/features/matches/components/match-score";
import { useMatchWebSocket } from "@/features/matches/hooks/use-match-ws";
import { cn } from "@/lib/utils";
import type { MatchDetail } from "@/types/match";
import type { ApiResponse } from "@/types/tournament";

interface Props {
  params: Promise<{ id: string }>;
}

export default function MatchDetailPage({ params }: Props) {
  const { id } = use(params);
  const [isConnected, setIsConnected] = useState(false);

  const { data: response, isLoading, error } = useQuery<ApiResponse<MatchDetail>>({
    queryKey: ["matches", "detail", id],
    queryFn: () => matchApi.get(id),
    staleTime: 30 * 1000,
  });

  // WebSocket で試合スコアをリアルタイム購読
  useMatchWebSocket({
    matchId: id,
    onScoreUpdate: () => setIsConnected(true),
    onMatchComplete: () => setIsConnected(true),
  });

  // WebSocket 接続確認（マウント後に readyState を確認）
  useEffect(() => {
    const timer = setTimeout(() => setIsConnected(true), 1000);
    return () => clearTimeout(timer);
  }, []);

  const match = response?.data;

  if (isLoading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <div className="h-80 animate-pulse rounded-2xl bg-white/5" />
      </div>
    );
  }

  if (error || !match) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-8 text-center">
          <p className="text-red-400">試合データの取得に失敗しました</p>
          <Link
            href="/tournaments"
            className="mt-3 inline-block text-sm text-brand-400 hover:text-brand-300"
          >
            大会一覧に戻る
          </Link>
        </div>
      </div>
    );
  }

  const isLive = match.status === "ongoing";

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      {/* パンくずリスト */}
      <nav className="mb-6 flex items-center gap-2 text-sm text-slate-400">
        <Link href="/tournaments" className="hover:text-white">
          大会一覧
        </Link>
        {match.tournament_id && (
          <>
            <ChevronRight className="h-3.5 w-3.5" />
            <Link href={`/tournaments/${match.tournament_id}`} className="hover:text-white">
              大会詳細
            </Link>
          </>
        )}
        <ChevronRight className="h-3.5 w-3.5" />
        <span className="text-white">試合詳細</span>
      </nav>

      {/* WebSocket 接続状態インジケーター */}
      {isLive && (
        <div className="mb-4 flex items-center justify-end gap-1.5">
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              isConnected ? "bg-green-400 animate-pulse" : "bg-slate-600",
            )}
          />
          <span className="flex items-center gap-1 text-xs text-slate-500">
            {isConnected ? (
              <>
                <Wifi className="h-3 w-3 text-green-400" />
                リアルタイム接続中
              </>
            ) : (
              <>
                <WifiOff className="h-3 w-3" />
                接続中...
              </>
            )}
          </span>
        </div>
      )}

      {/* スコアボード */}
      <MatchScore match={match} isLive={isLive} />

      {/* 配信リンク */}
      {(match.stream_url || match.vod_url) && (
        <div className="mt-4 flex gap-3">
          {match.stream_url && (
            <a
              href={match.stream_url}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-2 text-sm font-semibold text-red-400 hover:bg-red-500/20 transition-colors"
            >
              🔴 LIVE配信を見る
            </a>
          )}
          {match.vod_url && (
            <a
              href={match.vod_url}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-slate-400 hover:text-white transition-colors"
            >
              📹 VODを見る
            </a>
          )}
        </div>
      )}
    </div>
  );
}
