"use client";

import { use, useState, useEffect, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { ChevronRight, Wifi, WifiOff, LayoutDashboard, Map, Shield, BarChart2, Clock } from "lucide-react";
import { matchApi } from "@/features/matches/api/match-api";
import { cn } from "@/lib/utils";
import type { MatchDetail, WSMessage } from "@/types/match";
import type { ApiResponse } from "@/types/tournament";
import { MatchHero } from "./_components/match-hero";
import { OverviewTab } from "./_components/overview-tab";
import { MapsTab } from "./_components/maps-tab";
import { BanPickTab } from "./_components/banpick-tab";
import { StatisticsTab } from "./_components/statistics-tab";
import { TimelineTab } from "./_components/timeline-tab";
import { MatchResult } from "./_components/match-result";

type TabId = "overview" | "maps" | "banpick" | "statistics" | "timeline";

const TABS: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "maps", label: "Maps", icon: Map },
  { id: "banpick", label: "Ban/Pick", icon: Shield },
  { id: "statistics", label: "Statistics", icon: BarChart2 },
  { id: "timeline", label: "Timeline", icon: Clock },
];

const WS_BASE = typeof window !== "undefined" ? "" : (process.env.NEXT_PUBLIC_WS_URL ?? "");

interface Props {
  params: Promise<{ id: string }>;
}

export default function MatchSpectatorPage({ params }: Props) {
  const { id } = use(params);
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [wsStatus, setWsStatus] = useState<"connecting" | "connected" | "disconnected">("connecting");

  const { data: response, isLoading, error } = useQuery<ApiResponse<MatchDetail>>({
    queryKey: ["matches", "detail", id],
    queryFn: () => matchApi.get(id),
    staleTime: 30 * 1000,
    refetchInterval: (query) => query.state.data?.data?.status === "ongoing" ? 30000 : false,
  });

  // ── WebSocket リアルタイム更新 ─────────────────────────────────────────────
  const connect = useCallback(() => {
    const ws = new WebSocket(`/ws/matches/${id}`);
    setWsStatus("connecting");
    let retryTimer: ReturnType<typeof setTimeout>;

    ws.onopen = () => setWsStatus("connected");
    ws.onerror = () => setWsStatus("disconnected");
    ws.onclose = () => {
      setWsStatus("disconnected");
      retryTimer = setTimeout(connect, 3000);
    };
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string) as WSMessage;
        if (msg.type === "ping") { ws.send(JSON.stringify({ type: "pong" })); return; }
        if (msg.type === "score_update") {
          qc.setQueryData(["matches", "detail", id], (old: ApiResponse<MatchDetail> | undefined) => {
            if (!old) return old;
            return {
              ...old,
              data: {
                ...old.data,
                games: old.data.games.map((g) =>
                  g.game_number === msg.game_number
                    ? { ...g, team1_score: msg.team1_score, team2_score: msg.team2_score }
                    : g,
                ),
              },
            };
          });
        }
        if (msg.type === "match_complete") {
          qc.invalidateQueries({ queryKey: ["matches", "detail", id] });
        }
      } catch { /* ignore */ }
    };
    return () => { clearTimeout(retryTimer); ws.close(); };
  }, [id, qc]);

  useEffect(() => {
    const cleanup = connect();
    return cleanup;
  }, [connect]);

  const match = response?.data;

  if (isLoading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8 animate-pulse space-y-5">
        <div className="h-4 w-48 rounded bg-white/5" />
        <div className="h-48 rounded-2xl bg-white/5" />
        <div className="flex gap-2">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-10 w-24 rounded-full bg-white/5" />)}</div>
        <div className="h-64 rounded-xl bg-white/5" />
      </div>
    );
  }

  if (error || !match) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-16 text-center">
        <p className="text-slate-400">試合データの取得に失敗しました</p>
        <Link href="/tournaments" className="mt-3 inline-block text-sm text-brand-400 hover:text-brand-300">大会一覧に戻る</Link>
      </div>
    );
  }

  const isLive = match.status === "ongoing";
  const isCompleted = match.status === "completed";
  const team1Wins = match.games.filter((g) => g.winner_id === match.team1?.id).length;
  const team2Wins = match.games.filter((g) => g.winner_id === match.team2?.id).length;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* パンくず + WS状態 */}
      <div className="mb-5 flex items-center justify-between flex-wrap gap-3">
        <nav className="flex items-center gap-2 text-sm text-slate-400">
          <Link href="/tournaments" className="hover:text-white transition-colors">大会一覧</Link>
          {match.tournament_id && (
            <>
              <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
              <Link href={`/tournaments/${match.tournament_id}`} className="hover:text-white transition-colors">大会詳細</Link>
            </>
          )}
          <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
          <span className="text-white">試合観戦</span>
        </nav>
        {isLive && (
          <div className={cn(
            "flex items-center gap-1.5 rounded-full border px-3 py-1.5",
            wsStatus === "connected" ? "border-green-500/30 bg-green-500/5" : "border-white/10 bg-slate-900",
          )}>
            {wsStatus === "connected" ? (
              <><span className="h-2 w-2 animate-pulse rounded-full bg-green-400" /><Wifi className="h-3.5 w-3.5 text-green-400" /><span className="text-xs text-green-400">LIVE更新中</span></>
            ) : (
              <><WifiOff className="h-3.5 w-3.5 text-slate-500" /><span className="text-xs text-slate-500">{wsStatus === "connecting" ? "接続中..." : "切断"}</span></>
            )}
          </div>
        )}
      </div>

      {/* 試合終了バナー */}
      {isCompleted && (
        <div className="mb-5 rounded-xl border border-brand-500/20 bg-brand-500/5 px-4 py-3 text-sm">
          <span className="font-semibold text-brand-400">試合終了</span>
          <span className="ml-2 text-slate-400 text-xs">— MVP・チームスタッツはページ下部に表示されます</span>
        </div>
      )}

      {/* ヒーロー */}
      <MatchHero match={match} team1Wins={team1Wins} team2Wins={team2Wins} />

      {/* タブ */}
      <nav className="mt-5 flex overflow-x-auto border-b border-white/10 scrollbar-none" aria-label="試合詳細タブ">
        {TABS.map(({ id: tabId, label, icon: Icon }) => (
          <button
            key={tabId}
            onClick={() => setActiveTab(tabId)}
            className={cn(
              "flex flex-shrink-0 items-center gap-2 border-b-2 px-5 py-3 text-sm font-medium transition-colors",
              activeTab === tabId ? "border-brand-500 text-brand-400" : "border-transparent text-slate-500 hover:text-slate-300",
            )}
            aria-current={activeTab === tabId ? "page" : undefined}
          >
            <Icon className="h-4 w-4" />
            <span className="hidden sm:inline">{label}</span>
          </button>
        ))}
      </nav>

      {/* タブコンテンツ */}
      <div className="min-h-[300px]">
        {activeTab === "overview" && <OverviewTab match={match} />}
        {activeTab === "maps" && <MapsTab match={match} />}
        {activeTab === "banpick" && <BanPickTab match={match} />}
        {activeTab === "statistics" && <StatisticsTab match={match} />}
        {activeTab === "timeline" && <TimelineTab match={match} />}
      </div>

      {/* 試合終了後: MVP・サマリー・チームスタッツ */}
      {isCompleted && (
        <div className="mt-10 border-t border-white/10 pt-8">
          <h2 className="mb-6 text-lg font-black text-white">試合結果</h2>
          <MatchResult match={match} />
        </div>
      )}
    </div>
  );
}
