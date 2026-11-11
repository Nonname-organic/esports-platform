"use client";

import Link from "next/link";
import { Mail, Loader2, Check, X } from "lucide-react";
import { useRequireAuth } from "@/hooks/use-require-auth";
import { useMyTeamInvitations, useRespondInvitation } from "@/features/teams/hooks/use-teams";

const ROLE_LABEL: Record<string, string> = {
  captain: "キャプテン", player: "プレイヤー", substitute: "補欠", coach: "コーチ", analyst: "アナリスト",
};

/** 届いたチームへの招待。承認したときだけチームのメンバーになる（RC4） */
export default function TeamInvitationsPage() {
  const { ready, authed } = useRequireAuth();
  const { data: invitations, isLoading } = useMyTeamInvitations(ready && authed);
  const respond = useRespondInvitation();

  if (!ready || !authed) return null;

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="mb-6 flex items-center gap-3">
        <div className="rounded-xl bg-brand-500/10 p-2.5">
          <Mail className="h-6 w-6 text-brand-400" />
        </div>
        <div>
          <h1 className="text-xl font-black text-white">チームからの招待</h1>
          <p className="text-sm text-slate-500">承認するとチームのメンバーになります。断った招待は 7 日間届きません</p>
        </div>
      </div>

      {respond.isError && (
        <p role="alert" className="mb-4 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">
          {respond.error instanceof Error ? respond.error.message : "返事に失敗しました"}
        </p>
      )}

      {isLoading ? (
        <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-brand-500" /></div>
      ) : !invitations || invitations.length === 0 ? (
        <div className="rounded-xl border border-white/10 bg-slate-900 py-14 text-center text-sm text-slate-500">
          返事待ちの招待はありません
        </div>
      ) : (
        <div className="space-y-2">
          {invitations.map((inv) => (
            <div key={inv.id} className="flex flex-wrap items-center gap-3 rounded-xl border border-white/8 bg-slate-900 px-4 py-3">
              <div className="min-w-0 flex-1">
                <Link href={`/teams/${inv.team_id}`} className="font-semibold text-white hover:underline">
                  {inv.team_name}（{inv.team_tag}）
                </Link>
                <p className="text-xs text-slate-500">
                  {ROLE_LABEL[inv.role] ?? inv.role}として ・ 期限 {new Date(inv.expires_at).toLocaleDateString("ja-JP")}
                </p>
              </div>
              <button
                type="button"
                disabled={respond.isPending}
                onClick={() => respond.mutate({ id: inv.id, accept: true })}
                className="flex items-center gap-1 rounded-lg bg-brand-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
              >
                <Check className="h-3.5 w-3.5" /> 承認する
              </button>
              <button
                type="button"
                disabled={respond.isPending}
                onClick={() => respond.mutate({ id: inv.id, accept: false })}
                className="flex items-center gap-1 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:text-white disabled:opacity-50"
              >
                <X className="h-3.5 w-3.5" /> 断る
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
