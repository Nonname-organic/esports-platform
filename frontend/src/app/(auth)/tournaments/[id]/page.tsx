import { Suspense } from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { ChevronRight, Loader2 } from "lucide-react";
import { serverFetch } from "@/lib/api-client";
import type { ApiResponse, TournamentDetail, BracketResponse } from "@/types/tournament";
import { TournamentHeader } from "./_components/tournament-header";
import { TournamentTabs, type TabId } from "./_components/tournament-tabs";
import { CheckInButton } from "./_components/check-in-button";
import { OverviewTab } from "./_components/overview-tab";
import { MatchesTab } from "./_components/matches-tab";
import { BracketTab } from "./_components/bracket-tab";
import { StandingsTab } from "./_components/standings-tab";
import { AnalyticsTab } from "./_components/analytics-tab";

interface Props {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ tab?: string }>;
}

const VALID_TABS: TabId[] = ["overview", "matches", "bracket", "standings", "analytics"];

function isValidTab(tab: string | undefined): tab is TabId {
  return VALID_TABS.includes(tab as TabId);
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  try {
    const res = await serverFetch<ApiResponse<TournamentDetail>>(
      `/api/v1/tournaments/${id}`,
      undefined,
      { cache: "force-cache", next: { revalidate: 60 } },
    );
    const t = res.data;
    return {
      title: `${t.name} | EsportsPlatform`,
      description: t.description ?? `${t.game} ${t.format} tournament — ${t.registered_teams}/${t.max_teams} teams`,
      openGraph: {
        title: t.name,
        description: t.description ?? undefined,
        images: t.banner_url ? [{ url: t.banner_url }] : [],
      },
    };
  } catch {
    return { title: "大会詳細 | EsportsPlatform" };
  }
}

export default async function TournamentDetailPage({ params, searchParams }: Props) {
  const { id } = await params;
  const { tab: rawTab } = await searchParams;
  const activeTab: TabId = isValidTab(rawTab) ? rawTab : "overview";

  // SSR: 大会データ取得
  let tournament: TournamentDetail;
  try {
    const res = await serverFetch<ApiResponse<TournamentDetail>>(
      `/api/v1/tournaments/${id}`,
      undefined,
      { cache: "no-store" },
    );
    tournament = res.data;
  } catch (err: unknown) {
    if (err && typeof err === "object" && "status" in err && (err as { status: number }).status === 404) {
      notFound();
    }
    throw err;
  }

  // ブラケットをプリフェッチ（Bracket/Overview タブで使用）
  let initialBracket: BracketResponse | undefined;
  if (activeTab === "bracket" || activeTab === "overview") {
    try {
      const res = await serverFetch<ApiResponse<BracketResponse>>(
        `/api/v1/tournaments/${id}/bracket`,
        undefined,
        { cache: "no-store" },
      );
      initialBracket = res.data;
    } catch {
      // ブラケット未生成は正常ケース
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* パンくずリスト */}
      <nav aria-label="パンくずリスト" className="mb-6 flex items-center gap-2 text-sm text-slate-400">
        <Link href="/tournaments" className="hover:text-white transition-colors">
          大会一覧
        </Link>
        <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
        <span className="truncate text-white">{tournament.name}</span>
      </nav>

      {/* ヘッダー */}
      <TournamentHeader tournament={tournament} />

      {/* チェックイン（要チェックイン大会のみ・ログイン済み登録チームに表示） */}
      {tournament.require_check_in && <CheckInButton tournamentId={id} />}

      {/* タブナビゲーション */}
      <TournamentTabs activeTab={activeTab} id={id} />

      {/* タブコンテンツ */}
      <Suspense
        fallback={
          <div className="flex items-center justify-center py-24">
            <Loader2 className="h-8 w-8 animate-spin text-brand-500" />
          </div>
        }
      >
        {activeTab === "overview" && <OverviewTab tournament={tournament} />}
        {activeTab === "matches" && (
          <MatchesTab tournamentId={id} tournament={tournament} />
        )}
        {activeTab === "bracket" && (
          <BracketTab tournamentId={id} initialBracket={initialBracket} />
        )}
        {activeTab === "standings" && <StandingsTab tournamentId={id} />}
        {activeTab === "analytics" && <AnalyticsTab tournament={tournament} />}
      </Suspense>
    </div>
  );
}
