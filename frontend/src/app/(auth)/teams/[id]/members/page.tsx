"use client";

import { useState, use } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Users, UserPlus, Trash2, ChevronRight, AlertCircle, Shield, Loader2 } from "lucide-react";
import { useTeam, useTeamMembers, useAddMember, useRemoveMember } from "@/features/teams/hooks/use-teams";
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
  jersey_number: z.coerce.number().int().min(1).max(99).optional().or(z.literal("")),
});

type AddFormValues = z.infer<typeof addSchema>;

export default function TeamMembersPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const user = useAuthStore((s) => s.user);
  const { data: team, isLoading: teamLoading } = useTeam(id);
  const { data: members, isLoading: membersLoading } = useTeamMembers(id);
  const addMember = useAddMember(id);
  const removeMember = useRemoveMember(id);

  const [showAddForm, setShowAddForm] = useState(false);

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
      jersey_number: values.jersey_number ? Number(values.jersey_number) : undefined,
    });
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

  const isOwnerOrCaptain = user?.role === "admin" || String(team.id) === user?.id;

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      {/* パンくず */}
      <nav className="mb-6 flex items-center gap-2 text-sm text-slate-400">
        <Link href={`/teams/${id}`} className="hover:text-white transition-colors">{team.name}</Link>
        <ChevronRight className="h-3.5 w-3.5" />
        <span className="text-white">メンバー管理</span>
      </nav>

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

      {/* 招待フォーム */}
      {showAddForm && (
        <div className="mb-5 rounded-xl border border-brand-500/30 bg-slate-900 p-5">
          <h2 className="mb-4 text-sm font-bold text-white">メンバーを招待</h2>
          <form onSubmit={onAdd} className="space-y-4">
            {addMember.isError && (
              <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">
                <AlertCircle className="h-3.5 w-3.5" />
                {addMember.error instanceof Error ? addMember.error.message : "招待に失敗しました"}
              </div>
            )}

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
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

              <div>
                <label className="mb-1 block text-xs text-slate-500">背番号（任意）</label>
                <input
                  type="number"
                  {...register("jersey_number")}
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-brand-500"
                  placeholder="1-99"
                  min={1}
                  max={99}
                />
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
    </div>
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

      {(member as any).jersey_number && (
        <span className="text-xs text-slate-500">#{(member as any).jersey_number}</span>
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
