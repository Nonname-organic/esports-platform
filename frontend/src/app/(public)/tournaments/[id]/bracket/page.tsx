// SSR + CSR ハイブリッド:
// Server Component でブラケット初期データを取得し props として渡す
// Client Component (BracketView + useBracket) が 30秒ポーリングで自動更新

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { serverFetch } from "@/lib/api-client";
import { BracketPageClient } from "./_components/bracket-page-client";
import type { ApiResponse, BracketResponse, TournamentDetail } from "@/types/tournament";

interface Props {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  try {
    const res = await serverFetch<ApiResponse<TournamentDetail>>(
      `/api/v1/tournaments/${id}`,
      undefined,
      { cache: "no-store" },
    );
    return { title: `${res.data.name} - ブラケット` };
  } catch {
    return { title: "ブラケット" };
  }
}

export default async function BracketPage({ params }: Props) {
  const { id } = await params;

  // ブラケットデータ: SSR で初期データを取得（ハイドレーション後は 30秒ポーリング）
  let initialBracket: BracketResponse | null = null;
  let tournamentName = "大会";

  try {
    const [bracketRes, tournamentRes] = await Promise.allSettled([
      serverFetch<ApiResponse<BracketResponse>>(
        `/api/v1/tournaments/${id}/bracket`,
        undefined,
        { cache: "no-store" },
      ),
      serverFetch<ApiResponse<TournamentDetail>>(
        `/api/v1/tournaments/${id}`,
        undefined,
        { next: { revalidate: 60 } },
      ),
    ]);

    if (bracketRes.status === "fulfilled") {
      initialBracket = bracketRes.value.data;
    } else if (
      bracketRes.status === "rejected" &&
      bracketRes.reason &&
      typeof bracketRes.reason === "object" &&
      "status" in bracketRes.reason &&
      (bracketRes.reason as { status: number }).status === 404
    ) {
      notFound();
    }

    if (tournamentRes.status === "fulfilled") {
      tournamentName = tournamentRes.value.data.name;
    }
  } catch {
    notFound();
  }

  return (
    <div className="mx-auto max-w-full px-4 py-8">
      {/* パンくずリスト */}
      <nav className="mb-6 flex items-center gap-2 text-sm text-slate-400">
        <Link href="/tournaments" className="hover:text-white">
          大会一覧
        </Link>
        <ChevronRight className="h-3.5 w-3.5" />
        <Link href={`/tournaments/${id}`} className="hover:text-white">
          {tournamentName}
        </Link>
        <ChevronRight className="h-3.5 w-3.5" />
        <span className="text-white">ブラケット</span>
      </nav>

      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-black text-white">{tournamentName}</h1>
        <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-slate-400">
          30秒ごとに自動更新
        </span>
      </div>

      {/* SSRの初期データ + CSRポーリングで最新化するクライアントコンポーネント */}
      <BracketPageClient tournamentId={id} initialBracket={initialBracket} />
    </div>
  );
}
