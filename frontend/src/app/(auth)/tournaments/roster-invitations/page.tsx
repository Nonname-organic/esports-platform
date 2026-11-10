"use client";

import Link from "next/link";
import { ClipboardList, Loader2 } from "lucide-react";
import { useRequireAuth } from "@/hooks/use-require-auth";
import { useMyRosterInvitations, useRespondRoster } from "@/features/rosters/hooks/use-rosters";

/**
 * 大会の名簿への参加（RC4）。チームが名簿に載せても、本人が承認するまで出場登録には入らない。
 * 承認した後でも、名簿の固定（大会の開始）までは取り下げられる。
 */
export default function RosterInvitationsPage() {
  const { ready, authed } = useRequireAuth();
  const { data: rows, isLoading } = useMyRosterInvitations(ready && authed);
  const respond = useRespondRoster();

  if (!ready || !authed) return null;

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="mb-6 flex items-center gap-3">
        <div className="rounded-xl bg-brand-500/10 p-2.5">
          <ClipboardList className="h-6 w-6 text-brand-400" />
        </div>
        <div>
          <h1 className="text-xl font-black text-white">大会の名簿への参加</h1>
          <p className="text-sm text-slate-500">承認した大会の試合にだけ、出場登録されます</p>
        </div>
      </div>

      {respond.isError && (
        <p role="alert" className="mb-4 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">
          {respond.error instanceof Error ? respond.error.message : "返事に失敗しました"}
        </p>
      )}

      {isLoading ? (
        <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-brand-500" /></div>
      ) : !rows || rows.length === 0 ? (
        <div className="rounded-xl border border-white/10 bg-slate-900 py-14 text-center text-sm text-slate-500">
          返事待ち・参加中の名簿はありません
        </div>
      ) : (
        <div className="space-y-2">
          {rows.map((r) => (
            <div key={r.id} className="flex flex-wrap items-center gap-3 rounded-xl border border-white/8 bg-slate-900 px-4 py-3">
              <div className="min-w-0 flex-1">
                <Link href={`/tournaments/${r.tournament_id}`} className="font-semibold text-white hover:underline">
                  {r.tournament_name}
                </Link>
                <p className="text-xs text-slate-500">
                  {r.team_name} ・ {r.default_slot === "starter" ? "スターター" : "控え"}
                  {r.roster_locked_at ? " ・ 名簿は固定済み" : ""}
                </p>
              </div>
              {r.status === "invited" ? (
                <>
                  <button
                    type="button"
                    disabled={respond.isPending}
                    onClick={() => respond.mutate({ entryId: r.id, action: "accept" })}
                    className="rounded-lg bg-brand-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
                  >
                    参加を承認
                  </button>
                  <button
                    type="button"
                    disabled={respond.isPending}
                    onClick={() => respond.mutate({ entryId: r.id, action: "decline" })}
                    className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:text-white disabled:opacity-50"
                  >
                    辞退
                  </button>
                </>
              ) : (
                <>
                  <span className="text-xs font-semibold text-green-400">参加を承認済み</span>
                  {!r.roster_locked_at && (
                    <button
                      type="button"
                      disabled={respond.isPending}
                      onClick={() => {
                        if (window.confirm("この大会の名簿への参加を取り下げますか？")) {
                          respond.mutate({ entryId: r.id, action: "withdraw" });
                        }
                      }}
                      className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:text-white disabled:opacity-50"
                    >
                      取り下げる
                    </button>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
