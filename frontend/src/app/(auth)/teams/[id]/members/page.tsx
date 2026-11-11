"use client";

import { useState, use } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Users, UserPlus, Trash2, ChevronRight, AlertCircle, Loader2, History, Mail, X, CheckCircle2 } from "lucide-react";
import {
  useTeam, useTeamMembers, useInviteMember, useRemoveMember, useTeamInvitations, useCancelInvitation,
} from "@/features/teams/hooks/use-teams";
import { useTeamAudit } from "@/features/audit/hooks/use-audit";
import { AuditLogTable } from "@/components/audit-log-table";
import { useAuthStore } from "@/store/auth-store";
import { cn } from "@/lib/utils";
import type { TeamMember } from "@/types/team";

const ROLES = [
  { value: "captain", label: "キャプテン" },
  { value: "player", label: "プレイヤー" },
  { value: "substitute", label: "補欠" },
  { value: "coach", label: "コーチ" },
  { value: "analyst", label: "アナリスト" },
];

const ROLE_STYLE: Record<string, string> = {
  captain: "bg-yellow-500/10 text-yellow-400",
  player: "bg-brand-500/10 text-brand-400",
  substitute: "bg-slate-500/10 text-slate-400",
  coach: "bg-green-500/10 text-green-400",
  analyst: "bg-purple-500/10 text-purple-400",
};

const ROLE_LABEL: Record<string, string> = {
  captain: "キャプテン", player: "プレイヤー", substitute: "補欠",
  coach: "コーチ", analyst: "アナリスト",
};

const addSchema = z.object({
  username: z.string().min(1, "ユーザー名を入力"),
  role: z.enum(["captain", "player", "substitute", "coach", "analyst"] as const),
});

type AddFormValues = z.infer<typeof addSchema>;

export default function TeamMembersPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const user = useAuthStore((s) => s.user);
  const { data: team, isLoading: teamLoading } = useTeam(id);
  const { data: members, isLoading: membersLoading } = useTeamMembers(id);
  const addMember = useInviteMember(id);
  const removeMember = useRemoveMember(id);
  const isManager = !!team && (user?.role === "admin" || String(team.owner_id) === String(user?.id));
  const { data: invitations } = useTeamInvitations(id, isManager);
  const cancelInvitation = useCancelInvitation(id);
  const pending = (invitations ?? []).filter((i) => i.status === "pending");

  const [showAddForm, setShowAddForm] = useState(false);
  const [invitedName, setInvitedName] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<AddFormValues>({
    resolver: zodResolver(addSchema),
    defaultValues: { role: "player" },
  });

  const onAdd = handleSubmit(async (values) => {
    await addMember.mutateAsync({
      username: values.username,
      role: values.role,
    });
    setInvitedName(values.username);
    reset();
    setShowAddForm(false);
  });

  const handleRemove = async (member: TeamMember) => {
    const name = member.display_name || member.username || "このメンバー";
    if (!confirm(`${name} をチームから削除しますか？`)) return;
    if (!member.player_id) return;
    await removeMember.mutateAsync(String(member.player_id));
  };

  if (teamLoading || membersLoading) return (
    <div className="flex h-64 items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-brand-500" />
    </div>
  );

  if (!team) return <div className="p-8 text-center text-slate-400">チームが見つかりません</div>;

  const isOwnerOrCaptain = isManager;

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      {/* パンくず */}
      <nav className="mb-4 flex items-center gap-2 text-sm text-slate-400">
        <Link href={`/teams/${id}`} className="hover:text-white transition-colors">{team.name}</Link>
        <ChevronRight className="h-3.5 w-3.5" />
        <span className="text-white">チーム管理</span>
      </nav>

      {/* 管理サブナビ */}
      <div className="mb-6 flex gap-1 border-b border-white/10">
        <Link href={`/teams/${id}/members`} className="border-b-2 border-brand-500 px-4 py-2 text-sm font-semibold text-brand-400">
          メンバー管理
        </Link>
        <Link href={`/teams/${id}/edit`} className="border-b-2 border-transparent px-4 py-2 text-sm font-medium text-slate-400 hover:text-white">
          チーム編集
        </Link>
        <Link href={`/teams/${id}`} className="border-b-2 border-transparent px-4 py-2 text-sm font-medium text-slate-400 hover:text-white">
          公開ページ
        </Link>
      </div>

      {/* ヘッダー */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-brand-500/10 p-2">
            <Users className="h-6 w-6 text-brand-400" />
          </div>
          <div>
            <h1 className="text-xl font-black text-white">メンバー管理</h1>
            <p className="text-sm text-slate-500">{members?.length ?? 0} 名</p>
          </div>
        </div>

        {isOwnerOrCaptain && (
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="flex items-center gap-2 rounded-lg bg-brand-500/10 px-4 py-2 text-sm font-semibold text-brand-400 hover:bg-brand-500/20 transition-colors"
          >
            <UserPlus className="h-4 w-4" />
            メンバーを招待
          </button>
        )}
      </div>

      {invitedName && (
        <div role="status" className="mb-5 flex items-center gap-2 rounded-xl border border-green-500/20 bg-green-500/10 px-4 py-3 text-sm text-green-400">
          <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
          {invitedName} さんに招待を送りました。本人が承認するとメンバーになります
          <button type="button" onClick={() => setInvitedName(null)} className="ml-auto text-green-400/70 hover:text-green-300" aria-label="閉じる">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* 招待フォーム */}
      {showAddForm && (
        <div className="mb-5 rounded-xl border border-brand-500/30 bg-slate-900 p-5">
          <h2 className="mb-1 text-sm font-bold text-white">メンバーを招待</h2>
          <p className="mb-4 text-xs text-slate-500">
            招待を受け取った本人が承認したときにメンバーになります（招待の期限は 7 日）
          </p>
          <form onSubmit={onAdd} className="space-y-4">
            {addMember.isError && (
              <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">
                <AlertCircle className="h-3.5 w-3.5" />
                {addMember.error instanceof Error ? addMember.error.message : "招待に失敗しました"}
              </div>
            )}

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs text-slate-500">ユーザー名</label>
                <input
                  {...register("username")}
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-brand-500"
                  placeholder="player_one"
                />
                {errors.username && <p className="mt-1 text-xs text-red-400">{errors.username.message}</p>}
              </div>

              <div>
                <label className="mb-1 block text-xs text-slate-500">ロール</label>
                <select {...register("role")} className="w-full rounded-lg border border-white/10 bg-slate-800 px-3 py-2 text-sm text-white outline-none focus:border-brand-500">
                  {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              </div>
            </div>

            <div className="flex gap-2">
              <button
                type="submit"
                disabled={isSubmitting || addMember.isPending}
                className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600 transition-colors disabled:opacity-40"
              >
                {isSubmitting || addMember.isPending ? "招待中..." : "招待する"}
              </button>
              <button
                type="button"
                onClick={() => { setShowAddForm(false); addMember.reset(); }}
                className="rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
              >
                キャンセル
              </button>
            </div>
          </form>
        </div>
      )}

      {/* 返事待ちの招待（オーナー・管理者） */}
      {isOwnerOrCaptain && pending.length > 0 && (
        <section className="mb-5">
          <h2 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
            <Mail className="h-4 w-4 text-brand-400" /> 返事待ちの招待
          </h2>
          <div className="space-y-2">
            {pending.map((inv) => (
              <div key={inv.id} className="flex items-center gap-3 rounded-xl border border-white/8 bg-slate-900 px-4 py-2.5 text-sm">
                <span className="font-semibold text-white">{inv.invitee_username ?? "（ユーザー）"}</span>
                <span className="text-xs text-slate-500">{ROLE_LABEL[inv.role] ?? inv.role}</span>
                <span className="text-xs text-slate-600">期限 {new Date(inv.expires_at).toLocaleDateString("ja-JP")}</span>
                <button
                  type="button"
                  disabled={cancelInvitation.isPending}
                  onClick={() => cancelInvitation.mutate(inv.id)}
                  className="ml-auto rounded-lg border border-white/10 px-2.5 py-1 text-xs text-slate-400 hover:text-white disabled:opacity-50"
                >
                  取り消す
                </button>
              </div>
            ))}
          </div>
          {cancelInvitation.isError && (
            <p role="alert" className="mt-2 text-xs text-red-400">
              {cancelInvitation.error instanceof Error ? cancelInvitation.error.message : "取り消しに失敗しました"}
            </p>
          )}
        </section>
      )}

      {/* メンバー一覧 */}
      <div className="space-y-2">
        {!members || members.length === 0 ? (
          <div className="rounded-xl border border-white/10 bg-slate-900 py-16 text-center">
            <Users className="mx-auto mb-3 h-10 w-10 text-slate-700" />
            <p className="text-sm text-slate-500">メンバーがいません</p>
          </div>
        ) : (
          members.map((member) => (
            <MemberRow
              key={String(member.id)}
              member={member}
              canManage={isOwnerOrCaptain}
              onRemove={() => handleRemove(member)}
              isRemoving={removeMember.isPending}
            />
          ))
        )}
      </div>

      {/* 監査ログ（owner/captain/Admin のみ / ADR-0012） */}
      {isOwnerOrCaptain && <TeamAuditSection teamId={id} />}
    </div>
  );
}

function TeamAuditSection({ teamId }: { teamId: string }) {
  const { data: items, isLoading } = useTeamAudit(teamId);
  return (
    <section className="mt-8">
      <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
        <History className="h-4 w-4 text-brand-400" /> ログ
      </h2>
      <AuditLogTable items={items} isLoading={isLoading} />
    </section>
  );
}

function MemberRow({
  member, canManage, onRemove, isRemoving,
}: {
  member: TeamMember;
  canManage: boolean;
  onRemove: () => void;
  isRemoving: boolean;
}) {
  const role = (member as any).role ?? "player";

  return (
    <div className="flex items-center gap-4 rounded-xl border border-white/8 bg-slate-900 px-4 py-3">
      <div className="h-10 w-10 flex-shrink-0 overflow-hidden rounded-full border border-white/10 bg-slate-800 flex items-center justify-center">
        {member.avatar_url ? (
          <img src={member.avatar_url} alt={member.display_name ?? member.username ?? ""} className="h-full w-full object-cover" />
        ) : (
          <span className="text-sm font-bold text-slate-500">
            {(member.display_name || member.username || "?").charAt(0).toUpperCase()}
          </span>
        )}
      </div>

      <div className="flex-1 min-w-0">
        <p className="font-semibold text-white">{member.display_name || member.username || "Unknown"}</p>
        {(member as any).in_game_name && (
          <p className="text-xs text-slate-500">IGN: {(member as any).in_game_name}</p>
        )}
      </div>


      {member.consent === "unconfirmed" && (
        <span
          title="RC4 より前に登録された所属です。本人が「設定 → 所属の確認」で確認するまでは本人未確認と表示します"
          className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold text-amber-400"
        >
          本人未確認
        </span>
      )}

      <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-semibold", ROLE_STYLE[role] ?? "bg-slate-500/10 text-slate-400")}>
        {ROLE_LABEL[role] ?? role}
      </span>

      {canManage && (
        <button
          onClick={onRemove}
          disabled={isRemoving}
          className="rounded-lg p-1.5 text-slate-600 hover:bg-red-500/10 hover:text-red-400 transition-colors disabled:opacity-50"
          aria-label="メンバーを削除"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
