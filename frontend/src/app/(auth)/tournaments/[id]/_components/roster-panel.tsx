"use client";

import { useState } from "react";
import { ClipboardList, Loader2, Trash2 } from "lucide-react";
import { useTeamMembers } from "@/features/teams/hooks/use-teams";
import { useRoster, useRosterMutations } from "@/features/rosters/hooks/use-rosters";
import type { RosterEntry } from "@/features/rosters/api/roster-api";
import type { TournamentDetail } from "@/types/tournament";

const STATUS_LABEL: Record<RosterEntry["status"], { label: string; tone: string }> = {
  invited: { label: "本人の返事待ち", tone: "text-yellow-400" },
  accepted: { label: "参加を承認", tone: "text-green-400" },
  declined: { label: "辞退", tone: "text-slate-500" },
  withdrawn: { label: "取り下げ", tone: "text-slate-500" },
  removed: { label: "外した", tone: "text-slate-500" },
  expired: { label: "期限切れ", tone: "text-slate-500" },
};
const ACTIVE = new Set(["invited", "accepted"]);
const CONSENTED = new Set(["self", "invitation", "confirmed"]);

/** VALORANT の既定（出場 5・名簿 7）。ほかのゲームは主催者が大会の設定で入れる */
function limits(t: TournamentDetail): [number, number] | null {
  if (t.lineup_size) return [t.lineup_size, Math.max(t.roster_max ?? t.lineup_size, t.lineup_size)];
  return t.game === "VALORANT" ? [5, 7] : null;
}

/**
 * 大会の名簿（RC4）。チームのオーナー・キャプテンが、本人が承諾したメンバーを載せ、
 * 本人が「大会の名簿への参加」で承認する。試合の出場登録は、承認した選手から作られる。
 */
export function RosterPanel({ tournament, registrationId, teamId }: {
  tournament: TournamentDetail; registrationId: string; teamId: string;
}) {
  const tournamentId = String(tournament.id);
  const { data: entries, isLoading } = useRoster(tournamentId, registrationId);
  const { data: members } = useTeamMembers(teamId);
  const { add, update } = useRosterMutations(tournamentId, registrationId);
  const [playerId, setPlayerId] = useState("");
  const [slot, setSlot] = useState<"starter" | "bench">("starter");

  const locked = !!tournament.roster_locked_at;
  const lim = limits(tournament);
  const names = new Map((members ?? []).map((m) => [String(m.player_id), m.in_game_name || m.display_name || m.username || "—"]));
  const active = (entries ?? []).filter((e) => ACTIVE.has(e.status));
  const onRoster = new Set(active.map((e) => e.player_id));
  const candidates = (members ?? []).filter(
    (m) => m.player_id && !onRoster.has(String(m.player_id)) && CONSENTED.has(m.consent ?? ""),
  );
  const error = add.error ?? update.error;

  return (
    <div className="mt-4 border-t border-white/10 pt-4">
      <h4 className="mb-1 flex items-center gap-2 text-sm font-bold text-white">
        <ClipboardList className="h-4 w-4 text-brand-400" />
        大会の名簿
      </h4>
      <p className="mb-3 text-[11px] leading-relaxed text-slate-500">
        {lim ? `出場 ${lim[0]} 人・名簿は ${lim[1]} 人まで。` : "出場人数が未設定です（主催者に確認してください）。"}
        載せた選手が参加を承認すると、試合の出場登録に入ります。
        {locked ? " 名簿は固定されています。変更は主催者に依頼してください" : " 名簿は大会の開始で固定されます"}
      </p>

      {isLoading ? (
        <Loader2 className="h-4 w-4 animate-spin text-slate-500" />
      ) : (
        <ul className="space-y-1.5">
          {(entries ?? []).filter((e) => e.status !== "removed").map((e) => {
            const view = STATUS_LABEL[e.status];
            return (
              <li key={e.id} className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-2 text-xs">
                <span className="flex-1 truncate font-semibold text-white">{names.get(e.player_id) ?? "選手"}</span>
                {!locked && ACTIVE.has(e.status) ? (
                  <select
                    aria-label="既定の役目"
                    value={e.default_slot}
                    disabled={update.isPending}
                    onChange={(ev) => update.mutate({ entryId: e.id, default_slot: ev.target.value as "starter" | "bench" })}
                    className="rounded border border-white/10 bg-slate-800 px-1.5 py-0.5 text-[11px] text-slate-300"
                  >
                    <option value="starter">スターター</option>
                    <option value="bench">控え</option>
                  </select>
                ) : (
                  <span className="text-slate-500">{e.default_slot === "starter" ? "スターター" : "控え"}</span>
                )}
                <span className={view.tone}>{view.label}</span>
                {!locked && ACTIVE.has(e.status) && (
                  <button
                    type="button"
                    aria-label="名簿から外す"
                    disabled={update.isPending}
                    onClick={() => update.mutate({ entryId: e.id, remove: true })}
                    className="rounded p-1 text-slate-600 hover:bg-red-500/10 hover:text-red-400 disabled:opacity-50"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                )}
              </li>
            );
          })}
          {active.length === 0 && <li className="text-xs text-slate-500">まだ誰も載っていません</li>}
        </ul>
      )}

      {!locked && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <select
            aria-label="名簿に載せるメンバー"
            value={playerId}
            onChange={(e) => setPlayerId(e.target.value)}
            className="min-w-0 flex-1 rounded-lg border border-white/10 bg-slate-800 px-2 py-1.5 text-xs text-white"
          >
            <option value="">メンバーを選ぶ</option>
            {candidates.map((m) => (
              <option key={String(m.player_id)} value={String(m.player_id)}>
                {m.in_game_name || m.display_name || m.username}
              </option>
            ))}
          </select>
          <select
            aria-label="既定の役目"
            value={slot}
            onChange={(e) => setSlot(e.target.value as "starter" | "bench")}
            className="rounded-lg border border-white/10 bg-slate-800 px-2 py-1.5 text-xs text-white"
          >
            <option value="starter">スターター</option>
            <option value="bench">控え</option>
          </select>
          <button
            type="button"
            disabled={!playerId || add.isPending}
            onClick={() => add.mutate({ player_id: playerId, default_slot: slot }, { onSuccess: () => setPlayerId("") })}
            className="rounded-lg bg-brand-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
          >
            名簿に載せる
          </button>
        </div>
      )}
      {!locked && candidates.length === 0 && (members?.length ?? 0) > 0 && (
        <p className="mt-2 text-[11px] text-slate-500">
          載せられるのは、本人が承諾したメンバー（招待を承認・所属を確認した人）だけです
        </p>
      )}
      {error && (
        <p role="alert" className="mt-2 text-xs text-red-400">
          {error instanceof Error ? error.message : "名簿の変更に失敗しました"}
        </p>
      )}
    </div>
  );
}
