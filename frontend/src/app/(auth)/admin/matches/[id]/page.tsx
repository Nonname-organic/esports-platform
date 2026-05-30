import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import Link from "next/link";
import { ChevronRight, ExternalLink } from "lucide-react";
import { serverFetch } from "@/lib/api-client";
import type { ApiResponse, TournamentDetail } from "@/types/tournament";
import type { MatchDetail } from "@/types/match";
import { MatchAdminClient } from "./_components/match-admin-client";

interface Props {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  try {
    const res = await serverFetch<ApiResponse<MatchDetail>>(
      `/api/v1/matches/${id}`,
      undefined,
      { cache: "no-store" },
    );
    const m = res.data;
    return {
      title: `[管理] ${m.team1?.name ?? "TBD"} vs ${m.team2?.name ?? "TBD"} | EsportsPlatform`,
    };
  } catch {
    return { title: "試合管理 | EsportsPlatform" };
  }
}

export default async function MatchAdminPage({ params }: Props) {
  const { id } = await params;

  // 試合データ取得
  let match: MatchDetail;
  try {
    const res = await serverFetch<ApiResponse<MatchDetail>>(
      `/api/v1/matches/${id}`,
      undefined,
      { cache: "no-store" },
    );
    match = res.data;
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

  // トーナメント情報からゲーム種別を取得（マッププール表示用）
  let game = "VALORANT";
  try {
    const res = await serverFetch<ApiResponse<TournamentDetail>>(
      `/api/v1/tournaments/${match.tournament_id}`,
      undefined,
      { next: { revalidate: 300 } },
    );
    game = res.data.game;
  } catch {
    // ゲーム取得失敗時はデフォルトを使用
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* パンくずリスト */}
      <nav aria-label="パンくずリスト" className="mb-6 flex items-center gap-2 text-sm text-slate-400">
        <Link href="/dashboard" className="hover:text-white transition-colors">
          ダッシュボード
        </Link>
        <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
        <Link
          href={`/tournaments/${match.tournament_id}`}
          className="hover:text-white transition-colors"
        >
          大会
        </Link>
        <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
        <span className="text-white">試合管理</span>

        {/* 観戦ページリンク */}
        <Link
          href={`/matches/${id}`}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1 text-xs text-slate-400 hover:text-white transition-colors"
        >
          <ExternalLink className="h-3 w-3" />
          観戦ページ
        </Link>
      </nav>

      <div className="mb-4">
        <div className="flex items-center gap-2">
          <span className="rounded-lg bg-red-500/10 px-2.5 py-1 text-xs font-bold text-red-400 uppercase tracking-wider">
            Admin
          </span>
          <h1 className="text-xl font-black text-white">試合管理</h1>
        </div>
        <p className="mt-1 text-sm text-slate-500">
          Round {match.round_number} · {match.format} · ID: {id.slice(0, 8)}
        </p>
      </div>

      {/* メインクライアントコンポーネント */}
      <MatchAdminClient matchId={id} initialMatch={match} game={game} />
    </div>
  );
}
