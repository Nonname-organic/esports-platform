"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CalendarClock, Check, Clock, Loader2, Send, Users } from "lucide-react";
import { ApiError } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";
import { useMyTeams } from "@/features/teams/hooks/use-teams";
import { useMyRegistration, useRegisterTeam } from "@/features/tournaments/hooks/use-tournaments";
import type { RegistrationState } from "@/features/tournaments/api/tournament-api";
import type { TournamentDetail } from "@/types/tournament";

const CARD = "rounded-xl border border-white/10 bg-slate-900 p-5";

/** 申請後の表示。抽選大会では pending が「抽選待ち」の意味になる。 */
const STATE_VIEW: Record<RegistrationState, { label: string; note: string; tone: string }> = {
  pending: {
    label: "申請済み（審査中）",
    note: "主催者の承認・抽選の結果をお待ちください。結果は通知とこのページでお知らせします",
    tone: "text-yellow-400",
  },
  approved: {
    label: "参加確定",
    note: "参加が確定しました。大会当日はチェックイン時間内にチェックインしてください",
    tone: "text-green-400",
  },
  waitlisted: {
    label: "補欠",
    note: "定員に達したため補欠です。辞退が出た場合に繰り上がることがあります",
    tone: "text-slate-300",
  },
  rejected: {
    label: "今回は見送り",
    note: "今回はご参加いただけません。次の大会へのエントリーをお待ちしています",
    tone: "text-red-400",
  },
};

const APPROVAL_NOTE: Record<string, string> = {
  manual: "主催者が申請を1件ずつ確認して承認します",
  auto: "先着順で即時に参加が確定します（定員超過後は補欠）",
  lottery: "受付終了後に抽選し、当選チームのみ参加確定になります",
};

function fmt(iso: string | null | undefined): string {
  if (!iso) return "未定";
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}

interface EntryPanelProps {
  tournament: TournamentDetail;
}

/**
 * 大会へのエントリー欄。
 *
 * 受付期間と承認方式を明示したうえで、自分が代表を務めるチームを選んで
 * 申請する。申請後は当落（審査中・参加確定・補欠・見送り）をここに出す。
 */
export function EntryPanel({ tournament }: EntryPanelProps) {
  const { isAuthenticated, _hasHydrated } = useAuthStore();
  const authed = _hasHydrated && isAuthenticated;

  const tournamentId = String(tournament.id);
  const { data: registration } = useMyRegistration(tournamentId, authed);
  const { data: teams } = useMyTeams(authed);
  const register = useRegisterTeam(tournamentId);

  const [teamId, setTeamId] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  // チーム一覧が届いたら先頭を初期選択にしておく（1チームなら選ぶ手間が消える）
  useEffect(() => {
    if (!teamId && teams && teams.length > 0) setTeamId(String(teams[0].id));
  }, [teams, teamId]);

  const isOpen = tournament.status === "registration_open";

  const period = (
    <div className="mt-3 space-y-1 text-xs text-slate-400">
      <p className="flex items-center gap-1.5">
        <CalendarClock className="h-3.5 w-3.5 text-slate-500" />
        受付期間: <span className="font-semibold text-white">
          {fmt(tournament.registration_start_at)} 〜 {fmt(tournament.registration_end_at)}
        </span>
      </p>
      {tournament.approval_mode && APPROVAL_NOTE[tournament.approval_mode] && (
        <p className="text-[11px] text-slate-500">
          {APPROVAL_NOTE[tournament.approval_mode]}
        </p>
      )}
    </div>
  );

  // 申請済み: 当落をそのまま出す
  if (authed && registration?.registered && registration.status) {
    const view = STATE_VIEW[registration.status];
    return (
      <div className={CARD}>
        <h3 className="mb-1 flex items-center gap-2 font-bold text-white">
          <Check className={`h-4 w-4 ${view.tone}`} />
          エントリー状況
        </h3>
        <p className={`text-sm font-bold ${view.tone}`}>{view.label}</p>
        {registration.team_name && (
          <p className="mt-0.5 text-xs text-slate-400">
            申請チーム: <span className="text-white">{registration.team_name}</span>
          </p>
        )}
        <p className="mt-2 text-[11px] leading-relaxed text-slate-500">{view.note}</p>
      </div>
    );
  }

  // 受付していない期間: 何がいつ起きるかだけ伝える
  if (!isOpen) {
    return (
      <div className={CARD}>
        <h3 className="flex items-center gap-2 font-bold text-white">
          <Clock className="h-4 w-4 text-slate-400" />
          エントリー
        </h3>
        <p className="mt-1 text-xs text-slate-400">
          {tournament.status === "draft"
            ? "受付開始までお待ちください"
            : "この大会の受付は終了しています"}
        </p>
        {period}
      </div>
    );
  }

  // 未ログイン: 公開ページなので締め出さず、導線だけ出す
  if (!authed) {
    return (
      <div className="rounded-xl border border-brand-500/30 bg-slate-900 p-5">
        <h3 className="flex items-center gap-2 font-bold text-white">
          <Send className="h-4 w-4 text-brand-400" />
          エントリー受付中
        </h3>
        {period}
        <Link
          href={`/login?next=/tournaments/${tournamentId}`}
          className="mt-3 flex w-full items-center justify-center rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-bold text-white transition-colors hover:bg-brand-600"
        >
          ログインしてエントリー
        </Link>
      </div>
    );
  }

  // チーム未所属: 先にチームを作ってもらう
  if (teams && teams.length === 0) {
    return (
      <div className={CARD}>
        <h3 className="flex items-center gap-2 font-bold text-white">
          <Users className="h-4 w-4 text-brand-400" />
          エントリー受付中
        </h3>
        {period}
        <p className="mt-3 text-xs text-slate-400">
          エントリーにはチームが必要です。チームを作成してから申請してください
        </p>
        <Link
          href="/teams/create"
          className="mt-3 flex w-full items-center justify-center rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-bold text-white transition-colors hover:bg-brand-600"
        >
          チームを作成
        </Link>
      </div>
    );
  }

  const submit = async () => {
    if (!teamId) return;
    setError(null);
    try {
      await register.mutateAsync({ teamId, notes: notes.trim() || undefined });
      setNotes("");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "エントリーに失敗しました");
    }
  };

  return (
    <div className="rounded-xl border border-brand-500/30 bg-slate-900 p-5">
      <h3 className="flex items-center gap-2 font-bold text-white">
        <Send className="h-4 w-4 text-brand-400" />
        エントリー受付中
      </h3>
      {period}

      <label className="mt-4 block text-xs font-medium text-slate-400">
        参加するチーム
      </label>
      <select
        value={teamId}
        onChange={(e) => setTeamId(e.target.value)}
        className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-brand-500"
      >
        {(teams ?? []).map((t) => (
          <option key={String(t.id)} value={String(t.id)} className="bg-slate-900">
            {t.name}（{t.tag}）
          </option>
        ))}
      </select>

      <label className="mt-3 block text-xs font-medium text-slate-400">
        主催者への連絡事項（任意）
      </label>
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        rows={2}
        placeholder="出場メンバーの補足など"
        className="mt-1 w-full resize-none rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-slate-600 outline-none transition-colors focus:border-brand-500"
      />

      <button
        onClick={submit}
        disabled={register.isPending || !teamId}
        className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-bold text-white transition-colors hover:bg-brand-600 disabled:opacity-50"
      >
        {register.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
        エントリーする
      </button>
      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
    </div>
  );
}
