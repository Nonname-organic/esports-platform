import { Trophy, Zap } from "lucide-react";
import { cn, formatPrize, getGameColor, getStatusColor, getStatusLabel } from "@/lib/utils";
import type { TournamentDetail } from "@/types/tournament";

const FORMAT_LABEL: Record<string, string> = {
  single_elimination: "シングルエリミネーション",
  double_elimination: "ダブルエリミネーション",
  round_robin: "ラウンドロビン",
  swiss: "スイス式",
};

interface TournamentHeaderProps {
  tournament: TournamentDetail;
}

export function TournamentHeader({ tournament }: TournamentHeaderProps) {
  const isOngoing = tournament.status === "ongoing";
  const fillRate = Math.min((tournament.registered_teams / tournament.max_teams) * 100, 100);

  return (
    <div className="mb-6 overflow-hidden rounded-2xl border border-white/10 bg-slate-900">
      {/* バナー */}
      <div className="relative h-52 overflow-hidden bg-gradient-to-br from-slate-800 to-slate-950">
        {tournament.banner_url ? (
          <img
            src={tournament.banner_url}
            alt={tournament.name}
            className="h-full w-full object-cover opacity-40"
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <Trophy className="h-24 w-24 text-white/5" />
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-slate-900/60 to-transparent" />

        {/* バッジ群 */}
        <div className="absolute bottom-4 left-5 flex flex-wrap items-center gap-2">
          <span className={cn("rounded-full border px-3 py-1 text-xs font-bold", getGameColor(tournament.game))}>
            {tournament.game}
          </span>
          <span className={cn("inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold", getStatusColor(tournament.status))}>
            {isOngoing && <Zap className="h-3 w-3" />}
            {getStatusLabel(tournament.status)}
          </span>
          <span className="rounded-full border border-white/10 bg-black/30 px-3 py-1 text-xs text-slate-400">
            {FORMAT_LABEL[tournament.format] ?? tournament.format}
          </span>
        </div>

        {/* 賞金 */}
        {tournament.prize_pool != null && tournament.prize_pool > 0 && (
          <div className="absolute bottom-4 right-5 text-right">
            <p className="text-xs font-medium text-yellow-500/60 uppercase tracking-wider">Prize Pool</p>
            <p className="text-xl font-black text-yellow-400">{formatPrize(tournament.prize_pool)}</p>
          </div>
        )}
      </div>

      {/* タイトル + stats */}
      <div className="px-6 py-5">
        <h1 className="text-2xl font-black text-white">{tournament.name}</h1>
        {tournament.description && (
          <p className="mt-2 text-sm leading-relaxed text-slate-400 line-clamp-2">
            {tournament.description}
          </p>
        )}

        {/* 参加状況バー */}
        <div className="mt-4">
          <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
            <span>参加チーム</span>
            <span>
              <span className={cn("font-semibold", fillRate >= 100 ? "text-red-400" : "text-white")}>
                {tournament.registered_teams}
              </span>
              {" / "}{tournament.max_teams}
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
            <div
              className={cn("h-full rounded-full transition-all", fillRate >= 100 ? "bg-red-500" : "bg-brand-500")}
              style={{ width: `${fillRate}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
