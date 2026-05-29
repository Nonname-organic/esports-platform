"use client";

// 主催者ダッシュボード: CSR
// 主催者が管理する大会の一覧と各種ステータスを表示

import { useState } from "react";
import Link from "next/link";
import { Plus, Trophy, Users, ChevronRight, AlertCircle } from "lucide-react";
import { useTournaments, useCreateTournament, useGenerateBracket } from "@/features/tournaments/hooks/use-tournaments";
import { GameType } from "@/types/tournament";
import { useAuthStore } from "@/store/auth-store";
import { formatDate, getStatusColor, getStatusLabel } from "@/lib/utils";

export default function DashboardPage() {
  const { user } = useAuthStore();
  const [showCreateModal, setShowCreateModal] = useState(false);

  // 主催者の全大会を取得（APIではorganizer_idでフィルタされる想定）
  const { data, isLoading } = useTournaments();
  const createMutation = useCreateTournament();

  const tournaments = data?.pages.flatMap((p) => p.data) ?? [];

  return (
    <div className="px-4 py-8 sm:px-6 lg:px-8">
      {/* ページヘッダー */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white">ダッシュボード</h1>
          <p className="mt-0.5 text-sm text-slate-400">
            {user?.username} さん、おかえりなさい
          </p>
        </div>
        {(user?.role === "organizer" || user?.role === "admin") && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-600 transition-colors"
          >
            <Plus className="h-4 w-4" />
            大会を作成
          </button>
        )}
      </div>

      {/* サマリーカード */}
      <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          {
            label: "管理中の大会",
            value: tournaments.length,
            icon: Trophy,
            color: "text-brand-400",
          },
          {
            label: "開催中",
            value: tournaments.filter((t) => t.status === "ongoing").length,
            icon: AlertCircle,
            color: "text-red-400",
          },
          {
            label: "受付中",
            value: tournaments.filter((t) => t.status === "registration_open").length,
            icon: Users,
            color: "text-green-400",
          },
          {
            label: "完了",
            value: tournaments.filter((t) => t.status === "completed").length,
            icon: Trophy,
            color: "text-slate-400",
          },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="rounded-xl border border-white/10 bg-slate-900 p-4">
            <div className="flex items-center justify-between">
              <p className="text-xs text-slate-500">{label}</p>
              <Icon className={`h-4 w-4 ${color}`} />
            </div>
            <p className="mt-2 text-2xl font-black text-white">{value}</p>
          </div>
        ))}
      </div>

      {/* 大会リスト */}
      <div className="rounded-xl border border-white/10 bg-slate-900 overflow-hidden">
        <div className="border-b border-white/10 px-5 py-4">
          <h2 className="font-bold text-white">大会一覧</h2>
        </div>

        {isLoading ? (
          <div className="space-y-px">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-16 animate-pulse bg-white/5" />
            ))}
          </div>
        ) : tournaments.length === 0 ? (
          <div className="py-16 text-center">
            <Trophy className="mx-auto mb-3 h-10 w-10 text-slate-600" />
            <p className="text-sm text-slate-400">大会がありません</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="mt-3 text-sm text-brand-400 hover:text-brand-300"
            >
              最初の大会を作成する
            </button>
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {tournaments.map((t) => (
              <div
                key={t.id}
                className="flex items-center justify-between px-5 py-4 hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center gap-4 min-w-0">
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-white">{t.name}</p>
                    <div className="mt-0.5 flex items-center gap-2 text-xs text-slate-500">
                      <span>{t.game}</span>
                      <span>·</span>
                      <span>{t.registered_teams}/{t.max_teams} チーム</span>
                      {t.start_at && (
                        <>
                          <span>·</span>
                          <span>{formatDate(t.start_at)}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${getStatusColor(t.status)}`}
                  >
                    {getStatusLabel(t.status)}
                  </span>
                  <Link
                    href={`/tournaments/${t.id}`}
                    className="rounded-lg p-1.5 text-slate-500 hover:bg-white/10 hover:text-white transition-colors"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 大会作成モーダル (簡易版) */}
      {showCreateModal && (
        <CreateTournamentModal
          onClose={() => setShowCreateModal(false)}
          onSubmit={async (data) => {
            await createMutation.mutateAsync(data);
            setShowCreateModal(false);
          }}
          isPending={createMutation.isPending}
        />
      )}
    </div>
  );
}

interface CreateTournamentModalProps {
  onClose: () => void;
  onSubmit: (data: { name: string; game: GameType; format: string; max_teams: number }) => Promise<void>;
  isPending: boolean;
}

function CreateTournamentModal({ onClose, onSubmit, isPending }: CreateTournamentModalProps) {
  const [form, setForm] = useState<{ name: string; game: GameType; format: string; max_teams: number }>({
    name: "",
    game: "VALORANT",
    format: "single_elimination",
    max_teams: 16,
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-slate-900 p-6">
        <h2 className="mb-5 text-lg font-bold text-white">大会を作成</h2>

        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-400">大会名</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder-slate-600 outline-none focus:border-brand-500"
              placeholder="VALORANT 秋季大会 2025"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-400">ゲーム</label>
            <select
              value={form.game}
              onChange={(e) => setForm((f) => ({ ...f, game: e.target.value as GameType }))}
              className="w-full rounded-lg border border-white/10 bg-slate-800 px-3 py-2.5 text-sm text-white outline-none focus:border-brand-500"
            >
              {["VALORANT", "LOL", "APEX", "CS2", "OVERWATCH"].map((g) => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-400">形式</label>
            <select
              value={form.format}
              onChange={(e) => setForm((f) => ({ ...f, format: e.target.value }))}
              className="w-full rounded-lg border border-white/10 bg-slate-800 px-3 py-2.5 text-sm text-white outline-none focus:border-brand-500"
            >
              <option value="single_elimination">シングルエリミネーション</option>
              <option value="double_elimination">ダブルエリミネーション</option>
              <option value="round_robin">ラウンドロビン</option>
              <option value="swiss">スイス式</option>
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-400">最大チーム数</label>
            <select
              value={form.max_teams}
              onChange={(e) => setForm((f) => ({ ...f, max_teams: Number(e.target.value) }))}
              className="w-full rounded-lg border border-white/10 bg-slate-800 px-3 py-2.5 text-sm text-white outline-none focus:border-brand-500"
            >
              {[4, 8, 16, 32].map((n) => (
                <option key={n} value={n}>{n} チーム</option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-6 flex gap-3">
          <button
            onClick={onClose}
            disabled={isPending}
            className="flex-1 rounded-xl border border-white/10 py-2.5 text-sm font-semibold text-slate-400 hover:text-white transition-colors"
          >
            キャンセル
          </button>
          <button
            onClick={() => onSubmit(form)}
            disabled={isPending || !form.name.trim()}
            className="flex-1 rounded-xl bg-brand-500 py-2.5 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50 transition-colors"
          >
            {isPending ? "作成中..." : "作成する"}
          </button>
        </div>
      </div>
    </div>
  );
}
