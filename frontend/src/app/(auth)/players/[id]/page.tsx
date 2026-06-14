import { Suspense } from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { ChevronRight, Loader2 } from "lucide-react";
import { serverFetch } from "@/lib/api-client";
import type { Player, PlayerCareerStats } from "@/types/player";
import type { ApiResponse } from "@/types/tournament";
import { PlayerHeader } from "./_components/player-header";
import { PlayerTabs, type PlayerTabId } from "./_components/player-tabs";
import { OverviewTab } from "./_components/overview-tab";
import { TrendTab } from "./_components/trend-tab";
import { MatchHistoryTab } from "./_components/match-history-tab";
import { AgentsTab } from "./_components/agents-tab";
import { CareerTab } from "./_components/career-tab";
import { AchievementsTab } from "./_components/achievements-tab";
import { RiotTab } from "./_components/riot-tab";

interface Props {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ tab?: string }>;
}

const VALID_TABS: PlayerTabId[] = ["overview", "career", "achievements", "trend", "matches", "agents", "riot"];

function isValidTab(tab: string | undefined): tab is PlayerTabId {
  return VALID_TABS.includes(tab as PlayerTabId);
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  try {
    const res = await serverFetch<ApiResponse<Player>>(
      `/api/v1/players/${id}`,
      undefined,
      { cache: "force-cache", next: { revalidate: 60 } },
    );
    const p = res.data;
    return {
      title: `${p.display_name} | EsportsPlatform`,
      description: p.bio ?? `${p.game} プレイヤー${p.team_name ? ` — ${p.team_name}` : ""}`,
      openGraph: {
        title: p.display_name,
        images: p.avatar_url ? [{ url: p.avatar_url }] : [],
      },
    };
  } catch {
    return { title: "プレイヤー詳細 | EsportsPlatform" };
  }
}

export default async function PlayerDetailPage({ params, searchParams }: Props) {
  const { id } = await params;
  const { tab: rawTab } = await searchParams;
  const activeTab: PlayerTabId = isValidTab(rawTab) ? rawTab : "overview";

  // SSR: プレイヤー（必須）。存在しない場合のみ404。
  let player: Player;
  try {
    const playerRes = await serverFetch<ApiResponse<Player>>(
      `/api/v1/players/${id}`,
      undefined,
      { cache: "no-store" },
    );
    player = playerRes.data;
  } catch (err: unknown) {
    if (
      err &&
      typeof err === "object" &&
      "status" in err &&
      (err as { status: number }).status === 404
    ) {
      notFound();
    }
    throw err;
  }

  // スタッツは任意（未集計の新規プレイヤーでもページを404にしない）
  const EMPTY_STATS: PlayerCareerStats = {
    total_matches: 0, wins: 0, losses: 0, win_rate: 0, total_games: 0,
    avg_kills: 0, avg_deaths: 0, avg_assists: 0, avg_kda: 0, avg_score: 0,
    headshot_rate: 0, first_blood_rate: 0, most_played_agent: null, most_played_agent_games: 0,
  };
  let stats: PlayerCareerStats = EMPTY_STATS;
  try {
    const statsRes = await serverFetch<ApiResponse<PlayerCareerStats>>(
      `/api/v1/players/${id}/stats`,
      undefined,
      { cache: "no-store" },
    );
    stats = statsRes.data ?? EMPTY_STATS;
  } catch {
    // /stats 未集計・取得失敗は許容（空スタッツで表示）
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* パンくずリスト */}
      <nav
        aria-label="パンくずリスト"
        className="mb-6 flex items-center gap-2 text-sm text-slate-400"
      >
        <Link href="/tournaments" className="hover:text-white transition-colors">
          大会一覧
        </Link>
        <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
        {player.team_id && (
          <>
            <Link href={`/teams/${player.team_id}`} className="hover:text-white transition-colors">
              {player.team_name ?? "チーム"}
            </Link>
            <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
          </>
        )}
        <span className="truncate text-white">{player.display_name}</span>
      </nav>

      {/* ヘッダー */}
      <PlayerHeader player={player} stats={stats} />

      {/* タブナビゲーション */}
      <PlayerTabs activeTab={activeTab} id={id} />

      {/* タブコンテンツ */}
      <Suspense
        fallback={
          <div className="flex items-center justify-center py-24">
            <Loader2 className="h-8 w-8 animate-spin text-brand-500" />
          </div>
        }
      >
        {activeTab === "overview" && <OverviewTab player={player} stats={stats} />}
        {activeTab === "career" && <CareerTab playerId={id} />}
        {activeTab === "achievements" && <AchievementsTab playerId={id} />}
        {activeTab === "trend" && <TrendTab playerId={id} />}
        {activeTab === "matches" && <MatchHistoryTab playerId={id} />}
        {activeTab === "agents" && <AgentsTab playerId={id} />}
        {activeTab === "riot" && <RiotTab playerId={id} playerUserId={player.user_id ?? undefined} />}
      </Suspense>
    </div>
  );
}
