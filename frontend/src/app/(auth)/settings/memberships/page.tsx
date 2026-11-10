"use client";

import Link from "next/link";
import { ShieldCheck, Loader2 } from "lucide-react";
import { useRequireAuth } from "@/hooks/use-require-auth";
import { useMyMemberships, useDecideMembership } from "@/features/teams/hooks/use-teams";
import { cn } from "@/lib/utils";
import type { MembershipConsent } from "@/types/team";

const CONSENT_LABEL: Record<MembershipConsent, { label: string; tone: string }> = {
  self: { label: "本人が作成", tone: "text-green-400" },
  invitation: { label: "招待を承認", tone: "text-green-400" },
  confirmed: { label: "本人が確認済み", tone: "text-green-400" },
  unconfirmed: { label: "本人未確認", tone: "text-amber-400" },
  rejected: { label: "本人が否認", tone: "text-red-400" },
};

/**
 * 自分の所属の確認（RC4）。RC4 より前に登録された所属は「本人未確認」から始まり、
 * 期限までに確認しないと、大会の名簿・成績の帰属に数えられなくなる。
 */
export default function MembershipsPage() {
  const { ready, authed } = useRequireAuth();
  const { data, isLoading } = useMyMemberships(ready && authed);
  const decide = useDecideMembership();

  if (!ready || !authed) return null;

  const deadline = data?.deadline ? new Date(data.deadline).toLocaleDateString("ja-JP") : null;

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="mb-6 flex items-center gap-3">
        <div className="rounded-xl bg-brand-500/10 p-2.5">
          <ShieldCheck className="h-6 w-6 text-brand-400" />
        </div>
        <div>
          <h1 className="text-xl font-black text-white">所属の確認</h1>
          <p className="text-sm text-slate-500">
            本人未確認の所属は、確認するか否認してください{deadline ? `（期限 ${deadline}）` : ""}
          </p>
        </div>
      </div>

      <p className="mb-4 text-xs leading-relaxed text-slate-500">
        否認すると、その所属は脱退として扱い、その期間の大会の成績はあなたの実績に数えません。誤って否認したときは運営に連絡してください。
      </p>

      {decide.isError && (
        <p role="alert" className="mb-4 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">
          {decide.error instanceof Error ? decide.error.message : "操作に失敗しました"}
        </p>
      )}

      {isLoading ? (
        <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-brand-500" /></div>
      ) : !data || data.items.length === 0 ? (
        <div className="rounded-xl border border-white/10 bg-slate-900 py-14 text-center text-sm text-slate-500">
          所属しているチームはありません
        </div>
      ) : (
        <div className="space-y-2">
          {data.items.map((m) => {
            const view = CONSENT_LABEL[m.consent] ?? { label: m.consent, tone: "text-slate-400" };
            return (
              <div key={m.id} className="flex flex-wrap items-center gap-3 rounded-xl border border-white/8 bg-slate-900 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <Link href={`/teams/${m.team_id}`} className="font-semibold text-white hover:underline">
                    {m.team_name}（{m.team_tag}）
                  </Link>
                  <p className="text-xs text-slate-500">
                    {new Date(m.joined_at).toLocaleDateString("ja-JP")} から
                    {m.left_at ? ` ${new Date(m.left_at).toLocaleDateString("ja-JP")} まで` : ""}
                  </p>
                </div>
                <span className={cn("text-xs font-semibold", view.tone)}>{view.label}</span>
                {m.consent === "unconfirmed" && (
                  <>
                    <button
                      type="button"
                      disabled={decide.isPending}
                      onClick={() => decide.mutate({ id: m.id, confirm: true })}
                      className="rounded-lg bg-brand-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
                    >
                      自分の所属として確認
                    </button>
                    <button
                      type="button"
                      disabled={decide.isPending}
                      onClick={() => {
                        if (window.confirm(`${m.team_name} への所属を否認しますか？（脱退として扱います）`)) {
                          decide.mutate({ id: m.id, confirm: false });
                        }
                      }}
                      className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:text-white disabled:opacity-50"
                    >
                      否認する
                    </button>
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
