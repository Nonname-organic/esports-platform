"use client";

import { useState, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Trophy, ChevronRight, ChevronDown, CheckCircle2, XCircle, Clock, Users,
  Settings, Trash2, Zap, BarChart2, AlertCircle, Shield, History,
  RefreshCw, ExternalLink, FileText, Loader2, ScrollText,
} from "lucide-react";
import { tournamentApi, type RegistrationInfo } from "@/features/tournaments/api/tournament-api";
import { useTeamMembers } from "@/features/teams/hooks/use-teams";
import { useTournamentAudit } from "@/features/audit/hooks/use-audit";
import { AuditLogTable } from "@/components/audit-log-table";
import { RulesEditor } from "@/components/rules-editor";
import { cn, formatDate, getGameColor, getStatusLabel } from "@/lib/utils";
import type { TournamentStatus } from "@/types/tournament";

// ── ステータスフロー ───────────────────────────────────────────────────────────
const STATUS_FLOW: { status: TournamentStatus; label: string; icon: React.ElementType; color: string }[] = [
  { status: "draft", label: "下書き", icon: Clock, color: "text-slate-400" },
  { status: "registration_open", label: "受付中", icon: Users, color: "text-green-400" },
  { status: "registration_closed", label: "受付終了", icon: XCircle, color: "text-yellow-400" },
  { status: "ongoing", label: "開催中", icon: Zap, color: "text-red-400" },
  { status: "completed", label: "完了", icon: CheckCircle2, color: "text-slate-500" },
];

// ステータスは日程に応じてバックエンドが自動更新する（手動遷移は廃止）。
// 運営の手動操作は draft → 公開（registration_open）のみ。

// ── メンバー役割ラベル ───────────────────────────────────────────────────────
const MEMBER_ROLE_LABEL: Record<string, string> = {
  captain: "キャプテン", player: "プレイヤー", substitute: "補欠",
  coach: "コーチ", analyst: "アナリスト", manager: "マネージャー",
};

// ── ロスター展開 ─────────────────────────────────────────────────────────────
function RegistrationRoster({ teamId }: { teamId: string }) {
  const { data: members, isLoading } = useTeamMembers(teamId);

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 px-4 py-4 text-xs text-slate-500">
        <Loader2 className="h-3.5 w-3.5 animate-spin" /> メンバーを読み込み中...
      </div>
    );
  }
  if (!members || members.length === 0) {
    return <p className="px-4 py-4 text-xs text-slate-500">登録メンバーがいません</p>;
  }
  return (
    <div className="divide-y divide-white/5 border-t border-white/8">
      {members.map((m) => (
        <div key={m.id} className="flex items-center gap-3 px-4 py-2.5">
          <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center overflow-hidden rounded-full border border-white/10 bg-slate-800 text-xs font-bold text-slate-400">
            {m.avatar_url ? <img src={m.avatar_url} alt="" className="h-full w-full object-cover" /> : (m.in_game_name ?? m.username ?? "?").charAt(0)}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-white">
              {m.in_game_name ?? m.username ?? "Unknown"}
              {m.jersey_number != null && <span className="ml-1.5 text-xs text-slate-500">#{m.jersey_number}</span>}
            </p>
            {m.username && m.in_game_name && m.username !== m.in_game_name && (
              <p className="truncate text-xs text-slate-500">@{m.username}</p>
            )}
          </div>
          <span className="rounded-md bg-white/5 px-2 py-0.5 text-[10px] font-semibold text-slate-400">
            {MEMBER_ROLE_LABEL[m.role] ?? m.role}
          </span>
          {m.player_id && (
            <Link href={`/players/${m.player_id}`} target="_blank"
              className="rounded-md p-1 text-slate-500 hover:text-white transition-colors" title="プロフィール">
              <ExternalLink className="h-3.5 w-3.5" />
            </Link>
          )}
        </div>
      ))}
    </div>
  );
}

// ── 登録カード ─────────────────────────────────────────────────────────────────
function RegistrationRow({
  reg, onApprove, onReject, isPending,
}: {
  reg: RegistrationInfo;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  isPending: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  const statusColor = {
    pending: "text-yellow-400 bg-yellow-400/10",
    approved: "text-green-400 bg-green-400/10",
    rejected: "text-red-400 bg-red-400/10",
    withdrawn: "text-slate-400 bg-slate-400/10",
    waitlisted: "text-blue-400 bg-blue-400/10",
  }[reg.status];

  const statusLabel = {
    pending: "審査中",
    approved: "承認済",
    rejected: "却下",
    withdrawn: "取下げ",
    waitlisted: "補欠",
  }[reg.status];

  return (
    <div className="overflow-hidden rounded-xl border border-white/8 bg-slate-900/50">
      <div className="flex items-center gap-3 px-4 py-3">
        <button
          onClick={() => setExpanded((v) => !v)}
          className="flex flex-shrink-0 items-center justify-center rounded-md p-1 text-slate-500 hover:bg-white/5 hover:text-white transition-colors"
          title={expanded ? "閉じる" : "メンバーを表示"}
        >
          <ChevronDown className={cn("h-4 w-4 transition-transform", expanded && "rotate-180")} />
        </button>
        <div className="h-9 w-9 flex-shrink-0 overflow-hidden rounded-lg border border-white/10 bg-slate-800 flex items-center justify-center">
          {reg.team_logo_url ? (
            <img src={reg.team_logo_url} alt="" className="h-full w-full object-contain" />
          ) : (
            <span className="text-xs font-bold text-slate-500">{reg.team_tag.slice(0, 2)}</span>
          )}
        </div>
        <button onClick={() => setExpanded((v) => !v)} className="flex-1 min-w-0 text-left">
          <p className="font-semibold text-white">{reg.team_name}</p>
          <p className="text-xs text-slate-500">
            [{reg.team_tag}] · {new Date(reg.registered_at).toLocaleDateString("ja-JP")}
          </p>
        </button>
        <Link href={`/teams/${reg.team_id}`} target="_blank"
          className="hidden flex-shrink-0 items-center gap-1 rounded-lg border border-white/10 px-2.5 py-1.5 text-xs text-slate-400 hover:text-white transition-colors sm:flex">
          <ExternalLink className="h-3.5 w-3.5" /> チーム
        </Link>
        <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-semibold", statusColor)}>
          {statusLabel}
        </span>
        {reg.status === "pending" && (
          <div className="flex gap-1.5">
            <button
              onClick={() => onApprove(reg.id)}
              disabled={isPending}
              className="rounded-lg bg-green-500/10 p-1.5 text-green-400 hover:bg-green-500/20 transition-colors disabled:opacity-50"
              title="承認"
            >
              <CheckCircle2 className="h-4 w-4" />
            </button>
            <button
              onClick={() => onReject(reg.id)}
              disabled={isPending}
              className="rounded-lg bg-red-500/10 p-1.5 text-red-400 hover:bg-red-500/20 transition-colors disabled:opacity-50"
              title="却下"
            >
              <XCircle className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>

      {/* 申請メンバー（ロスター）: 主催者が中身を確認 */}
      {expanded && <RegistrationRoster teamId={reg.team_id} />}

      {/* 申請メモ */}
      {expanded && reg.notes && (
        <div className="border-t border-white/8 px-4 py-3">
          <p className="mb-1 text-xs font-semibold text-slate-500">申請メモ</p>
          <p className="text-sm text-slate-300 whitespace-pre-wrap">{reg.notes}</p>
        </div>
      )}
    </div>
  );
}

// ── メインページ ──────────────────────────────────────────────────────────────
export default function TournamentManagePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<"overview" | "registrations" | "bracket" | "rules" | "audit" | "settings">("overview");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const { data: tournamentRes, isLoading, refetch } = useQuery({
    queryKey: ["tournament", id],
    queryFn: () => tournamentApi.get(id),
    select: (res) => res.data,
  });

  const { data: regsRes, refetch: refetchRegs } = useQuery({
    queryKey: ["tournament-registrations", id],
    queryFn: () => tournamentApi.listRegistrations(id),
    select: (res) => res.data,
    enabled: activeTab === "registrations",
  });

  const { data: auditItems, isLoading: auditLoading } = useTournamentAudit(id, activeTab === "audit");

  const changeStatus = useMutation({
    mutationFn: (status: TournamentStatus) => tournamentApi.changeStatus(id, status),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["tournament", id] }); refetch(); },
  });

  const updateReg = useMutation({
    mutationFn: ({ regId, status }: { regId: string; status: "approved" | "rejected" }) =>
      tournamentApi.updateRegistration(id, regId, status),
    onSuccess: () => refetchRegs(),
  });

  const generateBracket = useMutation({
    mutationFn: () => tournamentApi.generateBracket(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tournament", id] });
      // 生成後はブラケット表示へ遷移して結果をすぐ確認できるようにする
      router.push(`/tournaments/${id}/bracket`);
    },
  });

  const deleteTournament = useMutation({
    mutationFn: () => tournamentApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tournaments", "mine"] });
      router.push("/dashboard");
    },
  });

  const tournament = tournamentRes;
  const registrations = regsRes ?? [];
  const pendingCount = registrations.filter((r) => r.status === "pending").length;
  const approvedCount = registrations.filter((r) => r.status === "approved").length;

  if (isLoading || !tournament) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  const currentStepIdx = STATUS_FLOW.findIndex((s) => s.status === tournament.status);

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      {/* パンくず */}
      <nav className="mb-6 flex items-center gap-2 text-sm text-slate-400">
        <Link href="/dashboard" className="hover:text-white transition-colors">ダッシュボード</Link>
        <ChevronRight className="h-3.5 w-3.5" />
        <span className="truncate text-white">{tournament.name}</span>
      </nav>

      {/* ヘッダー */}
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="rounded-2xl bg-brand-500/10 p-3">
            <Trophy className="h-7 w-7 text-brand-400" />
          </div>
          <div>
            <h1 className="text-xl font-black text-white">{tournament.name}</h1>
            <div className="mt-1 flex items-center gap-2">
              <span className={cn("rounded-full border px-2 py-0.5 text-xs font-bold", getGameColor(tournament.game))}>{tournament.game}</span>
              <span className="text-xs text-slate-500">{getStatusLabel(tournament.status)}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href={`/tournaments/${id}`}
            target="_blank"
            className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-400 hover:text-white transition-colors"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            公開ページ
          </Link>
          <button onClick={() => refetch()}
            className="rounded-lg border border-white/10 p-2 text-slate-400 hover:text-white transition-colors">
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* ステータス（手動変更） */}
      <div className="mb-6 rounded-2xl border border-white/10 bg-slate-900 p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-bold text-white">ステータス</h2>
          <span className="text-xs text-slate-500">クリックで変更できます</span>
        </div>

        {/* 現在のフロー表示 */}
        <div className="mb-4 flex items-center gap-2 overflow-x-auto pb-1">
          {STATUS_FLOW.map((s, i) => {
            const isDone = i < currentStepIdx;
            const isActive = i === currentStepIdx;
            return (
              <div key={s.status} className="flex flex-shrink-0 items-center gap-2">
                <div className={cn(
                  "flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold",
                  isActive ? cn("border border-brand-500/50 bg-brand-500/10", s.color) :
                    isDone ? "bg-green-500/10 text-green-400" : "bg-white/5 text-slate-600",
                )}>
                  <s.icon className="h-3.5 w-3.5" />
                  {s.label}
                </div>
                {i < STATUS_FLOW.length - 1 && (
                  <ChevronRight className={cn("h-3.5 w-3.5 flex-shrink-0", isDone ? "text-green-400" : "text-slate-700")} />
                )}
              </div>
            );
          })}
        </div>

        {/* 手動変更ボタン */}
        <div className="flex flex-wrap gap-2 border-t border-white/10 pt-4">
          {STATUS_FLOW.map((s) => {
            const isCurrent = tournament.status === s.status;
            return (
              <button
                key={s.status}
                onClick={() => { if (!isCurrent) changeStatus.mutate(s.status); }}
                disabled={changeStatus.isPending || isCurrent}
                className={cn(
                  "flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors",
                  isCurrent
                    ? "cursor-default border-brand-500/50 bg-brand-500/10 text-brand-400"
                    : "border-white/10 text-slate-400 hover:border-brand-500/40 hover:text-white disabled:opacity-40",
                )}
              >
                <s.icon className="h-3.5 w-3.5" />
                {isCurrent ? `${s.label}（現在）` : s.label}
              </button>
            );
          })}
        </div>
        {changeStatus.isError && (
          <p className="mt-2 text-xs text-red-400">
            {changeStatus.error instanceof Error ? changeStatus.error.message : "変更に失敗しました"}
          </p>
        )}
        <p className="mt-3 text-xs text-slate-600">
          ※ 手動で変更すると、日程による自動更新は行われなくなります。
        </p>
      </div>

      {/* 統計カード */}
      <div className="mb-6 grid grid-cols-3 gap-3">
        {[
          { label: "参加チーム", value: `${tournament.registered_teams}/${tournament.max_teams}`, color: "text-white" },
          { label: "申請中", value: pendingCount, color: pendingCount > 0 ? "text-yellow-400" : "text-slate-500" },
          { label: "承認済", value: approvedCount, color: "text-green-400" },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-xl border border-white/8 bg-slate-900 p-4 text-center">
            <p className={cn("text-2xl font-black", color)}>{value}</p>
            <p className="text-xs text-slate-500">{label}</p>
          </div>
        ))}
      </div>

      {/* タブ */}
      <nav className="mb-5 flex border-b border-white/10">
        {[
          { id: "overview", label: "概要", icon: BarChart2 },
          { id: "registrations", label: `参加申請${pendingCount > 0 ? ` (${pendingCount})` : ""}`, icon: Users },
          { id: "bracket", label: "ブラケット", icon: Shield },
          { id: "rules", label: "ルール", icon: ScrollText },
          { id: "audit", label: "ログ", icon: History },
          { id: "settings", label: "設定", icon: Settings },
        ].map(({ id: tabId, label, icon: Icon }) => (
          <button
            key={tabId}
            onClick={() => setActiveTab(tabId as typeof activeTab)}
            className={cn(
              "flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors",
              activeTab === tabId ? "border-brand-500 text-brand-400" : "border-transparent text-slate-500 hover:text-white",
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </nav>

      {/* 概要タブ */}
      {activeTab === "overview" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
            <h3 className="mb-4 text-sm font-bold text-white">大会情報</h3>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              {[
                { label: "形式", value: tournament.format },
                { label: "最大チーム数", value: `${tournament.max_teams}` },
                { label: "賞金", value: tournament.prize_pool ? `¥${Number(tournament.prize_pool).toLocaleString()}` : "なし" },
                { label: "チェックイン", value: tournament.require_check_in ? "必要" : "不要" },
                ...(tournament.start_at ? [{ label: "開始日", value: formatDate(tournament.start_at) }] : []),
                ...(tournament.registration_end_at ? [{ label: "受付終了", value: formatDate(tournament.registration_end_at) }] : []),
              ].map(({ label, value }) => (
                <div key={label}>
                  <dt className="text-slate-500">{label}</dt>
                  <dd className="mt-0.5 font-semibold text-white">{value}</dd>
                </div>
              ))}
            </dl>
          </div>
          {tournament.description && (
            <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
              <h3 className="mb-3 text-sm font-bold text-white">説明</h3>
              <p className="text-sm text-slate-300 whitespace-pre-wrap">{tournament.description}</p>
            </div>
          )}
          {tournament.attachments && tournament.attachments.length > 0 && (
            <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
              <h3 className="mb-3 text-sm font-bold text-white">添付ファイル</h3>
              <ul className="space-y-2">
                {tournament.attachments.map((f) => (
                  <li key={f.key}>
                    <a href={f.url} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-2.5 rounded-lg border border-white/10 bg-white/3 px-3 py-2.5 text-sm text-slate-300 hover:border-brand-500/40 hover:text-white transition-colors">
                      <FileText className="h-4 w-4 flex-shrink-0 text-brand-400" />
                      <span className="truncate">{f.name}</span>
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* 参加申請タブ */}
      {activeTab === "registrations" && (
        <div className="space-y-3">
          {registrations.length === 0 ? (
            <div className="flex h-40 flex-col items-center justify-center rounded-xl border border-white/10 bg-slate-900">
              <Users className="mb-2 h-8 w-8 text-slate-700" />
              <p className="text-sm text-slate-500">参加申請がありません</p>
            </div>
          ) : (
            <>
              {pendingCount > 0 && (
                <div className="flex items-center gap-2 rounded-xl border border-yellow-500/20 bg-yellow-500/5 px-4 py-3 text-sm text-yellow-400">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  {pendingCount}件の申請が審査待ちです
                </div>
              )}
              {registrations.map((reg) => (
                <RegistrationRow
                  key={reg.id}
                  reg={reg}
                  onApprove={(regId) => updateReg.mutate({ regId, status: "approved" })}
                  onReject={(regId) => updateReg.mutate({ regId, status: "rejected" })}
                  isPending={updateReg.isPending}
                />
              ))}
            </>
          )}
        </div>
      )}

      {/* ブラケットタブ */}
      {activeTab === "bracket" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
            <h3 className="mb-3 text-sm font-bold text-white">ブラケット生成</h3>
            <p className="mb-4 text-sm text-slate-400">
              参加受付終了後にブラケットを生成できます。
              現在 {approvedCount} チームが承認されています。
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => generateBracket.mutate()}
                disabled={generateBracket.isPending || !["registration_closed", "check_in", "ongoing"].includes(tournament.status)}
                className="flex items-center gap-2 rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-40 transition-colors"
              >
                <Shield className="h-4 w-4" />
                {generateBracket.isPending ? "生成中..." : "ブラケット生成"}
              </button>
              <Link
                href={`/tournaments/${id}/bracket`}
                className="flex items-center gap-2 rounded-xl border border-white/10 px-4 py-2.5 text-sm text-slate-300 hover:text-white transition-colors"
              >
                <ExternalLink className="h-4 w-4" />
                ブラケットを見る
              </Link>
            </div>
            {generateBracket.isError && (
              <p className="mt-2 text-xs text-red-400">
                {generateBracket.error instanceof Error ? generateBracket.error.message : "生成に失敗しました"}
              </p>
            )}
          </div>
        </div>
      )}

      {/* ルールタブ */}
      {activeTab === "rules" && (
        <div className="space-y-3">
          <p className="text-xs text-slate-500">
            Section構造でルールを編集します。入力した内容は公開ページの「Rules」タブに表示されます。
          </p>
          <RulesEditor tournamentId={id} />
        </div>
      )}

      {/* 監査ログタブ */}
      {activeTab === "audit" && (
        <div className="space-y-3">
          <p className="text-xs text-slate-500">この大会に対する操作履歴（主催者・Admin のみ閲覧可）</p>
          <AuditLogTable items={auditItems} isLoading={auditLoading} />
        </div>
      )}

      {/* 設定タブ */}
      {activeTab === "settings" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
            <h3 className="mb-3 text-sm font-bold text-white">大会設定</h3>
            <Link
              href={`/organizer/tournaments/${id}/edit`}
              className="flex items-center gap-2 rounded-lg border border-white/10 px-4 py-3 text-sm text-slate-300 hover:border-white/20 hover:text-white transition-colors"
            >
              <Settings className="h-4 w-4" />
              大会情報を編集
            </Link>
          </div>

          <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-5">
            <h3 className="mb-2 text-sm font-bold text-red-400">危険な操作</h3>
            <p className="mb-4 text-xs text-slate-500">大会を削除すると全データが失われ、復元できません。</p>
            {!showDeleteConfirm ? (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                disabled={tournament.status === "ongoing"}
                className="flex items-center gap-2 rounded-lg border border-red-500/30 px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 disabled:opacity-40 transition-colors"
              >
                <Trash2 className="h-4 w-4" />
                大会を削除
              </button>
            ) : (
              <div className="space-y-3">
                <p className="text-sm font-semibold text-red-400">本当に削除しますか？</p>
                <div className="flex gap-2">
                  <button
                    onClick={() => deleteTournament.mutate()}
                    disabled={deleteTournament.isPending}
                    className="rounded-lg bg-red-500 px-4 py-2 text-sm font-bold text-white hover:bg-red-600 disabled:opacity-50 transition-colors"
                  >
                    {deleteTournament.isPending ? "削除中..." : "削除する"}
                  </button>
                  <button
                    onClick={() => setShowDeleteConfirm(false)}
                    className="rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
                  >
                    キャンセル
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
