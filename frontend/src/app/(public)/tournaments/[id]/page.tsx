// SSR: cache: "no-store" で常に最新データを取得
// 参加登録状態は認証ユーザーによって変わるため、エッジキャッシュ不可

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Calendar, Users, Trophy, ChevronRight } from "lucide-react";
import Link from "next/link";
import { serverFetch } from "@/lib/api-client";
import { formatDate, formatPrize, getGameColor, getStatusColor, getStatusLabel } from "@/lib/utils";
import type { ApiResponse, TournamentDetail } from "@/types/tournament";

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
    return {
      title: res.data.name,
      description: res.data.description ?? undefined,
    };
  } catch {
    return { title: "大会詳細" };
  }
}

export default async function TournamentDetailPage({ params }: Props) {
  const { id } = await params;

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

  const registrationFull = tournament.registered_teams >= tournament.max_teams;
  const registrationPct = Math.min(
    (tournament.registered_teams / tournament.max_teams) * 100,
    100,
  );

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* パンくずリスト */}
      <nav className="mb-6 flex items-center gap-2 text-sm text-slate-400">
        <Link href="/tournaments" className="hover:text-white">
          大会一覧
        </Link>
        <ChevronRight className="h-3.5 w-3.5" />
        <span className="text-white">{tournament.name}</span>
      </nav>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* メイン情報 */}
        <div className="lg:col-span-2 space-y-6">
          {/* ヘッダーカード */}
          <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-slate-900">
            {tournament.banner_url ? (
              <img
                src={tournament.banner_url}
                alt={tournament.name}
                className="h-48 w-full object-cover opacity-50"
              />
            ) : (
              <div className="flex h-48 items-center justify-center bg-gradient-to-br from-slate-800 to-slate-900">
                <Trophy className="h-20 w-20 text-white/10" />
              </div>
            )}
            <div className="p-6">
              <div className="mb-2 flex flex-wrap gap-2">
                <span
                  className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${getGameColor(tournament.game)}`}
                >
                  {tournament.game}
                </span>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${getStatusColor(tournament.status)}`}
                >
                  {getStatusLabel(tournament.status)}
                </span>
                <span className="rounded-full border border-white/10 px-2.5 py-0.5 text-xs text-slate-400">
                  {tournament.format.replace("_", " ")}
                </span>
              </div>
              <h1 className="text-2xl font-black text-white">{tournament.name}</h1>
              {tournament.description && (
                <p className="mt-3 text-sm leading-relaxed text-slate-400">
                  {tournament.description}
                </p>
              )}
            </div>
          </div>

          {/* ブラケットへのリンク */}
          {(tournament.status === "ongoing" || tournament.status === "completed") && (
            <Link
              href={`/tournaments/${id}/bracket`}
              className="flex items-center justify-between rounded-xl border border-brand-500/30 bg-brand-500/10 px-5 py-4 hover:bg-brand-500/20 transition-colors"
            >
              <div className="flex items-center gap-3">
                <Trophy className="h-5 w-5 text-brand-400" />
                <span className="font-semibold text-white">ブラケットを見る</span>
              </div>
              <ChevronRight className="h-5 w-5 text-brand-400" />
            </Link>
          )}
        </div>

        {/* サイドバー情報 */}
        <div className="space-y-4">
          {/* 参加状況 */}
          <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
            <h3 className="mb-4 font-bold text-white">参加状況</h3>
            <div className="mb-3 flex items-end justify-between">
              <div>
                <span className={registrationFull ? "text-2xl font-black text-red-400" : "text-2xl font-black text-white"}>
                  {tournament.registered_teams}
                </span>
                <span className="text-slate-400"> / {tournament.max_teams} チーム</span>
              </div>
              {registrationFull && (
                <span className="text-xs font-semibold text-red-400">満員</span>
              )}
            </div>
            <div className="h-2 rounded-full bg-white/10">
              <div
                className={`h-full rounded-full transition-all ${registrationFull ? "bg-red-500" : "bg-brand-500"}`}
                style={{ width: `${registrationPct}%` }}
              />
            </div>
          </div>

          {/* 日程 */}
          <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
            <h3 className="mb-4 font-bold text-white">日程</h3>
            <dl className="space-y-3 text-sm">
              {[
                { label: "参加受付開始", value: tournament.registration_start_at },
                { label: "参加受付終了", value: tournament.registration_end_at },
                { label: "大会開始", value: tournament.start_at },
                { label: "大会終了", value: tournament.end_at },
              ].map(({ label, value }) => (
                <div key={label} className="flex items-start justify-between gap-2">
                  <dt className="text-slate-500">{label}</dt>
                  <dd className="text-right text-white">
                    {value ? formatDate(value) : "未定"}
                  </dd>
                </div>
              ))}
            </dl>
          </div>

          {/* 賞金 */}
          {tournament.prize_pool && (
            <div className="rounded-xl border border-yellow-500/20 bg-yellow-500/5 p-5">
              <p className="text-xs font-semibold text-yellow-500/60 uppercase tracking-wider">
                Prize Pool
              </p>
              <p className="mt-1 text-2xl font-black text-yellow-400">
                {formatPrize(tournament.prize_pool)}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
