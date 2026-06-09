import { Suspense } from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { ChevronRight, Loader2 } from "lucide-react";
import { serverFetch } from "@/lib/api-client";
import type { Team, TeamStats } from "@/types/team";
import type { ApiResponse } from "@/types/tournament";
import { TeamHeader } from "./_components/team-header";
import { TeamTabs, type TeamTabId } from "./_components/team-tabs";
import { OverviewTab } from "./_components/overview-tab";
import { PlayersTab } from "./_components/players-tab";
import { MatchesTab } from "./_components/matches-tab";
import { AnalyticsTab } from "./_components/analytics-tab";
import { CareerTab } from "./_components/career-tab";
import { RivalsTab } from "./_components/rivals-tab";

interface Props {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ tab?: string }>;
}

const VALID_TABS: TeamTabId[] = ["overview", "career", "players", "rivals", "matches", "analytics"];

function isValidTab(tab: string | undefined): tab is TeamTabId {
  return VALID_TABS.includes(tab as TeamTabId);
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  try {
    const res = await serverFetch<ApiResponse<Team>>(
      `/api/v1/teams/${id}`,
      undefined,
      { cache: "force-cache", next: { revalidate: 60 } },
    );
    const t = res.data;
    return {
      title: `${t.name} [${t.tag}] | EsportsPlatform`,
      description: t.description ?? `${t.game} チーム`,
      openGraph: {
        title: `${t.name} [${t.tag}]`,
        images: t.logo_url ? [{ url: t.logo_url }] : [],
      },
    };
  } catch {
    return { title: "チーム詳細 | EsportsPlatform" };
  }
}

export default async function TeamDetailPage({ params, searchParams }: Props) {
  const { id } = await params;
  const { tab: rawTab } = await searchParams;
  const activeTab: TeamTabId = isValidTab(rawTab) ? rawTab : "overview";

  // SSR: チームデータ + 統計を並列取得
  let team: Team;
  let stats: TeamStats;

  try {
    const [teamRes, statsRes] = await Promise.all([
      serverFetch<ApiResponse<Team>>(
        `/api/v1/teams/${id}`,
        undefined,
        { cache: "no-store" },
      ),
      serverFetch<ApiResponse<TeamStats>>(
        `/api/v1/teams/${id}/stats`,
        undefined,
        { cache: "no-store" },
      ),
    ]);
    team = teamRes.data;
    stats = statsRes.data;
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
        <span className="truncate text-white">{team.name}</span>
      </nav>

      {/* ヘッダー */}
      <TeamHeader team={team} stats={stats} />

      {/* タブナビゲーション */}
      <TeamTabs activeTab={activeTab} id={id} />

      {/* タブコンテンツ */}
      <Suspense
        fallback={
          <div className="flex items-center justify-center py-24">
            <Loader2 className="h-8 w-8 animate-spin text-brand-500" />
          </div>
        }
      >
        {activeTab === "overview" && <OverviewTab team={team} stats={stats} />}
        {activeTab === "career" && <CareerTab teamId={id} />}
        {activeTab === "players" && <PlayersTab teamId={id} />}
        {activeTab === "rivals" && <RivalsTab teamId={id} />}
        {activeTab === "matches" && <MatchesTab teamId={id} />}
        {activeTab === "analytics" && <AnalyticsTab teamId={id} />}
      </Suspense>
    </div>
  );
}
