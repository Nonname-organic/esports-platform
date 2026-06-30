"use client";

import Link from "next/link";
import { Plus, Shield, Users } from "lucide-react";
import { useRequireAuth } from "@/hooks/use-require-auth";
import { useMyTeams } from "@/features/teams/hooks/use-teams";
import { cn, getGameColor } from "@/lib/utils";

export default function MyTeamsPage() {
  const { ready, authed } = useRequireAuth();
  const { data: teams, isLoading } = useMyTeams();

  if (!ready || !authed) return null;

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-brand-500/10 p-2.5">
            <Users className="h-6 w-6 text-brand-400" />
          </div>
          <div>
            <h1 className="text-xl font-black text-white">マイチーム</h1>
            <p className="text-sm text-slate-500">作成・参加中のチーム</p>
          </div>
        </div>
        <Link
          href="/teams/create"
          className="flex items-center gap-2 rounded-xl bg-brand-500 px-4 py-2 text-sm font-bold text-white hover:bg-brand-600 transition-colors"
        >
          <Plus className="h-4 w-4" /> チームを作成
        </Link>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
        </div>
      ) : !teams || teams.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-white/10 py-20 text-center">
          <Shield className="mx-auto mb-4 h-12 w-12 text-slate-700" />
          <p className="text-sm font-semibold text-slate-400">まだチームがありません</p>
          <p className="mt-1 text-xs text-slate-600">チームを作成するか、チームに参加してください</p>
          <Link
            href="/teams/create"
            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-bold text-white hover:bg-brand-600 transition-colors"
          >
            <Plus className="h-4 w-4" /> チームを作成
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {teams.map((team) => (
            <div
              key={team.id}
              className="flex items-center gap-4 rounded-2xl border border-white/10 bg-slate-900 p-4 hover:border-white/20 transition-colors"
            >
              {/* ロゴ */}
              <div className="h-12 w-12 flex-shrink-0 overflow-hidden rounded-xl border border-white/10 bg-slate-800">
                {team.logo_url ? (
                  <img src={team.logo_url} alt={team.name} className="h-full w-full object-contain p-1" />
                ) : (
                  <div className="flex h-full w-full items-center justify-center">
                    <Shield className="h-6 w-6 text-slate-600" />
                  </div>
                )}
              </div>

              {/* 情報 */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm font-bold text-white">{team.name}</span>
                  <span className="text-xs text-slate-500">[{team.tag}]</span>
                  <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-bold", getGameColor(team.game))}>
                    {team.game}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-slate-500">
                  {team.owner_id ? "オーナー" : "メンバー"}
                </p>
              </div>

              {/* アクション */}
              <div className="flex items-center gap-2 flex-shrink-0">
                <Link
                  href={`/teams/${team.id}`}
                  className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:text-white hover:border-white/20 transition-colors"
                >
                  公開ページ
                </Link>
                <Link
                  href={`/teams/${team.id}/members`}
                  className="rounded-lg bg-brand-500/10 px-3 py-1.5 text-xs font-semibold text-brand-400 hover:bg-brand-500/20 transition-colors"
                >
                  メンバー管理
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
