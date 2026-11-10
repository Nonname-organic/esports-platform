"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeftRight, Users } from "lucide-react";
import { rosterApi, type Substitution } from "@/features/rosters/api/roster-api";
import { rosterKeys, useLineups, useSubstitutions } from "@/features/rosters/hooks/use-rosters";
import { cn } from "@/lib/utils";
import type { MatchDetail } from "@/types/match";

const KIND_LABEL: Record<Substitution["kind"], string> = {
  between_maps: "マップの間の交代",
  mid_map: "マップの途中の交代",
  fill: "補充（足りない人数を埋める）",
};
const STATUS_LABEL: Record<Substitution["status"], string> = {
  requested: "申請中", approved: "承認", rejected: "却下",
};

/**
 * 出場登録と交代（RC4・主催者）。開始で固定した出場登録を見せ、交代を理由つきで記録する。
 * チームからの交代の申請はここで承認・却下する。成績を書けるのは、そのマップに出た選手だけ。
 */
export function LineupPanel({ match }: { match: MatchDetail }) {
  const qc = useQueryClient();
  const { data: lineup } = useLineups(match.id);
  const { data: subs } = useSubstitutions(match.id, !!lineup?.locked_at);
  const teams = [match.team1, match.team2].filter(Boolean) as { id: string; name: string }[];
  const [teamId, setTeamId] = useState("");
  const [game, setGame] = useState(1);
  const [kind, setKind] = useState<Substitution["kind"]>("between_maps");
  const [outId, setOutId] = useState("");
  const [inId, setInId] = useState("");
  const [reason, setReason] = useState("");

  const refresh = () => {
    qc.invalidateQueries({ queryKey: rosterKeys.lineups(match.id) });
    qc.invalidateQueries({ queryKey: rosterKeys.substitutions(match.id) });
  };
  const submit = useMutation({
    mutationFn: () => rosterApi.submitSubstitution(match.id, game, {
      team_id: teamId, kind, out_player_id: kind === "fill" ? null : outId, in_player_id: inId,
      reason: reason.trim() || undefined,
    }),
    onSuccess: () => { setOutId(""); setInId(""); setReason(""); refresh(); },
  });
  const decide = useMutation({
    mutationFn: ({ id, approve }: { id: string; approve: boolean }) =>
      rosterApi.decideSubstitution(match.id, id, approve ? "approve" : "reject"),
    onSuccess: refresh,
  });

  if (!lineup || !lineup.locked_at) {
    return (
      <div className="rounded-xl border border-white/10 bg-slate-900 p-4 text-xs text-slate-500">
        <Users className="mr-1 inline h-3.5 w-3.5" />
        出場登録は試合の開始で固定されます（名簿の既定の役目から作ります）
      </div>
    );
  }

  const entries = lineup.entries;
  const nameOf = new Map(entries.map((e) => [e.id, e.in_game_name ?? "選手"]));
  const teamEntries = entries.filter((e) => e.team_id === teamId);

  return (
    <div className="space-y-4 rounded-xl border border-white/10 bg-slate-900 p-4">
      <h3 className="flex items-center gap-2 text-sm font-bold text-white">
        <Users className="h-4 w-4 text-brand-400" /> 出場登録と交代
      </h3>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {teams.map((t) => (
          <div key={t.id} className="rounded-lg bg-white/5 p-3">
            <p className="mb-1 text-xs font-bold text-white">{t.name}</p>
            {(["starter", "bench"] as const).map((slot) => (
              <p key={slot} className="text-xs text-slate-400">
                <span className="text-slate-500">{slot === "starter" ? "スターター" : "控え"}: </span>
                {entries.filter((e) => e.team_id === t.id && e.slot === slot).map((e) => e.in_game_name ?? "選手").join("、") || "—"}
              </p>
            ))}
          </div>
        ))}
      </div>

      {(subs ?? []).length > 0 && (
        <ul className="space-y-1.5">
          {(subs ?? []).map((s) => (
            <li key={s.id} className="flex flex-wrap items-center gap-2 rounded-lg bg-white/5 px-3 py-2 text-xs text-slate-300">
              <span className="font-semibold">マップ {s.game_number}</span>
              <span>{KIND_LABEL[s.kind]}</span>
              <span>
                {s.out_lineup_entry_id ? `${nameOf.get(s.out_lineup_entry_id)} → ` : "＋ "}
                {nameOf.get(s.in_lineup_entry_id)}
              </span>
              <span className={cn(s.status === "approved" ? "text-green-400" : s.status === "rejected" ? "text-slate-500" : "text-yellow-400")}>
                {STATUS_LABEL[s.status]}
              </span>
              {s.status === "requested" && (
                <span className="ml-auto flex gap-1">
                  <button type="button" disabled={decide.isPending} onClick={() => decide.mutate({ id: s.id, approve: true })}
                    className="rounded bg-brand-500 px-2 py-0.5 text-white disabled:opacity-50">承認</button>
                  <button type="button" disabled={decide.isPending} onClick={() => decide.mutate({ id: s.id, approve: false })}
                    className="rounded border border-white/10 px-2 py-0.5 text-slate-400 disabled:opacity-50">却下</button>
                </span>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="space-y-2 border-t border-white/10 pt-3">
        <p className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
          <ArrowLeftRight className="h-3.5 w-3.5" /> 交代を記録する（主催者の記録は理由が必須）
        </p>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <select aria-label="チーム" value={teamId} onChange={(e) => { setTeamId(e.target.value); setOutId(""); setInId(""); }}
            className="rounded-lg border border-white/10 bg-slate-800 px-2 py-1.5 text-xs text-white">
            <option value="">チーム</option>
            {teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
          <select aria-label="マップ" value={game} onChange={(e) => setGame(Number(e.target.value))}
            className="rounded-lg border border-white/10 bg-slate-800 px-2 py-1.5 text-xs text-white">
            {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>マップ {n}</option>)}
          </select>
          <select aria-label="種類" value={kind} onChange={(e) => setKind(e.target.value as Substitution["kind"])}
            className="col-span-2 rounded-lg border border-white/10 bg-slate-800 px-2 py-1.5 text-xs text-white">
            {(Object.keys(KIND_LABEL) as Substitution["kind"][]).map((k) => <option key={k} value={k}>{KIND_LABEL[k]}</option>)}
          </select>
          {kind !== "fill" && (
            <select aria-label="抜ける選手" value={outId} onChange={(e) => setOutId(e.target.value)}
              className="col-span-2 rounded-lg border border-white/10 bg-slate-800 px-2 py-1.5 text-xs text-white">
              <option value="">抜ける選手</option>
              {teamEntries.map((e) => <option key={e.id} value={e.player_id}>{e.in_game_name ?? "選手"}</option>)}
            </select>
          )}
          <select aria-label="入る選手" value={inId} onChange={(e) => setInId(e.target.value)}
            className="col-span-2 rounded-lg border border-white/10 bg-slate-800 px-2 py-1.5 text-xs text-white">
            <option value="">入る選手</option>
            {teamEntries.map((e) => <option key={e.id} value={e.player_id}>{e.in_game_name ?? "選手"}</option>)}
          </select>
        </div>
        <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="理由（必須）" aria-label="交代の理由"
          className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white outline-none focus:border-brand-500" />
        <button type="button"
          disabled={!teamId || !inId || (kind !== "fill" && !outId) || !reason.trim() || submit.isPending}
          onClick={() => submit.mutate()}
          className="rounded-lg bg-brand-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-600 disabled:opacity-40">
          {submit.isPending ? "記録中..." : "交代を記録"}
        </button>
        {(submit.error ?? decide.error) && (
          <p role="alert" className="text-xs text-red-400">
            {(submit.error ?? decide.error) instanceof Error ? (submit.error ?? decide.error)!.message : "記録できませんでした"}
          </p>
        )}
      </div>
    </div>
  );
}
