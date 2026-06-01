"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Trophy, Plus, Users, Zap, Clock, PlayCircle, Settings,
  Search, Calendar,
} from "lucide-react";
import { tournamentApi } from "@/features/tournaments/api/tournament-api";
import { useAuthStore } from "@/store/auth-store";
import { cn, formatDate, getGameColor, getStatusColor, getStatusLabel } from "@/lib/utils";
import type { TournamentDetail, TournamentStatus } from "@/types/tournament";

const STATUS_NEXT: Partial<Record<TournamentStatus, { next: TournamentStatus; label: string }>> = {
  draft: { next: "registration_open", label: "受付開始" },
  registration_open: { next: "registration_closed", label: "受付終了" },
  registration_closed: { next: "ongoing", label: "開催開始" },
  check_in: { next: "ongoing", label: "開催開始" },
  ongoing: { next: "completed", label: "完了にする" },
};

function TournamentCard({
  tournament, onStatusChange,
}: {
  tournament: TournamentDetail;
  onStatusChange: (id: string, status: TournamentStatus) => void;
}) {
  const next = STATUS_NEXT[tournament.status as TournamentStatus];
  const fillPct = tournament.max_teams > 0
    ? Math.min((tournament.registered_teams / tournament.max_teams) * 100, 100)
    : 0;

  return (
    <div className="overflow-hidden rounded-2xl border border-white/8 bg-slate-900 transition-all hover:border-white/15">
      <div className="relative h-20 bg-gradient-to-br from-slate-800 to-slate-950">
        {tournament.banner_url && (
          <img src={tournament.banner_url} alt="" className="h-full w-full object-cover opacity-25" />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-900 to-transparent" />
        <div className="absolute left-3 top-3">
          <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-bold", getGameColor(tournament.game))}>{tournament.game}</span>
        </div>
        <div className="absolute right-3 top-3">
          <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-bold", getStatusColor(tournament.status))}>{getStatusLabel(tournament.status)}</span>
        </div>
      </div>
      <div className="p-4">
        <h3 className="mb-1 font-bold text-white line-clamp-1">{tournament.name}</h3>
        <div className="mb-3 flex items-center gap-3 text-xs text-slate-500">
          <span>{tournament.registered_teams}/{tournament.max_teams} チーム</span>
          {tournament.start_at && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {new Date(tournament.start_at).toLocaleDateString("ja-JP", { month: "short", day: "numeric" })}
            </span>
          )}
        </div>
        <div className="mb-3 h-1 overflow-hidden rounded-full bg-white/10">
          <div className={cn("h-full rounded-full", fillPct >= 100 ? "bg-red-500" : "bg-brand-500")} style={{ width: `${fillPct}%` }} />
        </div>
        <div className="flex gap-2">
          <Link
            href={`/organizer/tournaments/${tournament.id}`}
            className="flex flex-1 items-center justify-center gap-1 rounded-lg border border-white/10 py-2 text-xs font-semibold text-slate-300 hover:border-brand-500/40 hover:text-brand-400 transition-colors"
          >
            <Settings className="h-3.5 w-3.5" />管理
          </Link>
          {next && (
            <button
              onClick={() => onStatusChange(String(tournament.id), next.next)}
              className="flex flex-1 items-center justify-center gap-1 rounded-lg bg-brand-500/10 py-2 text-xs font-semibold text-brand-400 hover:bg-brand-500/20 transition-colors"
            >
              <PlayCircle className="h-3.5 w-3.5" />{next.label}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const hasRole = useAuthStore((s) => s.hasRole);
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<TournamentStatus | "all">("all");

  const isOrganizer = hasRole("organizer", "admin");

  const { data, isLoading } = useQuery({
    queryKey: ["tournaments", "mine"],
    queryFn: () => tournamentApi.mine(),
    select: (res) => res.data,
    enabled: isOrganizer,
  });

  const changeStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: TournamentStatus }) =>
      tournamentApi.changeStatus(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tournaments", "mine"] }),
  });

  const tournaments = data ?? [];
  const filtered = tournaments.filter((t) => {
    if (filter !== "all" && t.status !== filter) return false;
    if (search && !t.name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const stats = {
    total: tournaments.length,
    ongoing: tournaments.filter((t) => t.status === "ongoing").length,
    open: tournaments.filter((t) => t.status === "registration_open").length,
    draft: tournaments.filter((t) => t.status === "draft").length,
  };

  return (
    <div className="min-h-screen bg-slate-950 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-white">ダッシュボード</h1>
          <p className="mt-0.5 text-sm text-slate-500">{user?.username} の大会管理</p>
        </div>
        <button
          onClick={() => router.push("/organizer/tournaments/new")}
          className="flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-bold text-white hover:bg-brand-600 transition-colors"
        >
          <Plus className="h-4 w-4" />大会を作成
        </button>
      </div>

      {/* KPI */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: "総大会数", value: stats.total, icon: Trophy, color: "text-brand-400", bg: "bg-brand-500/10" },
          { label: "開催中", value: stats.ongoing, icon: Zap, color: "text-red-400", bg: "bg-red-500/10" },
          { label: "受付中", value: stats.open, icon: Users, color: "text-green-400", bg: "bg-green-500/10" },
          { label: "下書き", value: stats.draft, icon: Clock, color: "text-slate-400", bg: "bg-slate-500/10" },
        ].map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="rounded-2xl border border-white/8 bg-slate-900 p-4">
            <div className={cn("mb-2 inline-flex rounded-xl p-2", bg)}>
              <Icon className={cn("h-5 w-5", color)} />
            </div>
            <p className="text-2xl font-black text-white">{value}</p>
            <p className="text-xs text-slate-500">{label}</p>
          </div>
        ))}
      </div>

      {/* Filter */}
      <div className="mb-5 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="大会名で検索..."
            className="w-full rounded-xl border border-white/10 bg-slate-900 py-2.5 pl-9 pr-4 text-sm text-white placeholder-slate-600 outline-none focus:border-brand-500" />
        </div>
        <div className="flex gap-1 rounded-xl border border-white/10 bg-slate-900 p-1">
          {(["all", "draft", "registration_open", "ongoing", "completed"] as const).map((s) => (
            <button key={s} onClick={() => setFilter(s as TournamentStatus | "all")}
              className={cn("rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors",
                filter === s ? "bg-brand-500 text-white" : "text-slate-500 hover:text-white")}>
              {s === "all" ? "すべて" : getStatusLabel(s)}
            </button>
          ))}
        </div>
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-56 animate-pulse rounded-2xl bg-white/5" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center py-20 text-center">
          <div className="mb-4 rounded-2xl bg-brand-500/10 p-5">
            <Trophy className="h-12 w-12 text-brand-400" />
          </div>
          <h3 className="text-lg font-bold text-white">
            {search || filter !== "all" ? "該当する大会がありません" : "まだ大会がありません"}
          </h3>
          <p className="mt-2 text-sm text-slate-400">最初の大会を作成してコミュニティを盛り上げましょう</p>
          {!search && filter === "all" && (
            <button onClick={() => router.push("/organizer/tournaments/new")}
              className="mt-5 flex items-center gap-2 rounded-xl bg-brand-500 px-6 py-3 text-sm font-bold text-white hover:bg-brand-600 transition-colors">
              <Plus className="h-4 w-4" />大会を作成
            </button>
          )}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((t) => (
            <TournamentCard key={String(t.id)} tournament={t}
              onStatusChange={(id, status) => changeStatus.mutate({ id, status })} />
          ))}
        </div>
      )}
    </div>
  );
}
