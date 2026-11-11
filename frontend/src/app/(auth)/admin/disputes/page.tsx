"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Scale } from "lucide-react";
import { rosterApi, type ParticipationDispute } from "@/features/rosters/api/roster-api";
import { rosterKeys, useDisputes } from "@/features/rosters/hooks/use-rosters";
import { useAuthStore } from "@/store/auth-store";
import { cn } from "@/lib/utils";

const TABS: { status: ParticipationDispute["status"]; label: string }[] = [
  { status: "open", label: "裁定待ち" },
  { status: "upheld", label: "認めた" },
  { status: "dismissed", label: "退けた" },
];

/**
 * 出場の異議の裁定（RC4・C5。管理者だけ）。認めると、その試合のその選手の成績は
 * 個人の通算・実績・RP に数えなくなる（行は消さない）。
 */
export default function AdminDisputesPage() {
  const router = useRouter();
  const hasRole = useAuthStore((s) => s.hasRole);
  const hasHydrated = useAuthStore((s) => s._hasHydrated);
  const isAdmin = hasHydrated && hasRole("admin");
  const [status, setStatus] = useState<ParticipationDispute["status"]>("open");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const { data: rows, isLoading } = useDisputes(status, isAdmin);
  const qc = useQueryClient();
  const resolve = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: "upheld" | "dismissed" }) =>
      rosterApi.resolveDispute(id, decision, notes[id]?.trim() || undefined),
    onSuccess: () => qc.invalidateQueries({ queryKey: rosterKeys.all }),
  });

  useEffect(() => {
    if (hasHydrated && !hasRole("admin")) router.replace("/dashboard");
  }, [hasHydrated, hasRole, router]);

  if (!isAdmin) return null;

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6 flex items-center gap-3">
        <div className="rounded-xl bg-red-500/10 p-2.5"><Scale className="h-6 w-6 text-red-400" /></div>
        <div>
          <h1 className="text-xl font-black text-white">出場の異議</h1>
          <p className="text-sm text-slate-500">認めると、その試合の本人の成績を個人の記録に数えなくなります</p>
        </div>
      </div>

      <nav className="mb-4 flex gap-1 border-b border-white/10">
        {TABS.map((t) => (
          <button key={t.status} type="button" onClick={() => setStatus(t.status)}
            className={cn("border-b-2 px-4 py-2 text-sm", status === t.status
              ? "border-brand-500 font-semibold text-brand-400" : "border-transparent text-slate-400 hover:text-white")}>
            {t.label}
          </button>
        ))}
      </nav>

      {resolve.isError && (
        <p role="alert" className="mb-3 text-xs text-red-400">
          {resolve.error instanceof Error ? resolve.error.message : "裁定できませんでした"}
        </p>
      )}

      {isLoading ? (
        <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-brand-500" /></div>
      ) : !rows || rows.length === 0 ? (
        <div className="rounded-xl border border-white/10 bg-slate-900 py-14 text-center text-sm text-slate-500">ありません</div>
      ) : (
        <div className="space-y-2">
          {rows.map((d) => (
            <div key={d.id} className="space-y-2 rounded-xl border border-white/8 bg-slate-900 px-4 py-3 text-sm">
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                <Link href={`/matches/${d.match_id}`} className="text-brand-400 hover:underline">試合を開く</Link>
                <Link href={`/players/${d.player_id}`} className="text-brand-400 hover:underline">選手</Link>
                <span>{new Date(d.created_at).toLocaleString("ja-JP")}</span>
              </div>
              <p className="whitespace-pre-wrap text-slate-200">{d.reason}</p>
              {d.status === "open" ? (
                <div className="flex flex-wrap items-center gap-2">
                  <input
                    value={notes[d.id] ?? ""}
                    onChange={(e) => setNotes({ ...notes, [d.id]: e.target.value })}
                    placeholder="裁定のメモ（本人には送らない）"
                    aria-label="裁定のメモ"
                    className="min-w-0 flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white outline-none focus:border-brand-500"
                  />
                  <button type="button" disabled={resolve.isPending} onClick={() => resolve.mutate({ id: d.id, decision: "upheld" })}
                    className="rounded-lg bg-brand-500 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">認める</button>
                  <button type="button" disabled={resolve.isPending} onClick={() => resolve.mutate({ id: d.id, decision: "dismissed" })}
                    className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:text-white disabled:opacity-50">退ける</button>
                </div>
              ) : (
                d.resolution_note && <p className="text-xs text-slate-500">メモ: {d.resolution_note}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
