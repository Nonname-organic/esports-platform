import Link from "next/link";
import { Calendar, Users, Trophy } from "lucide-react";
import { cn, formatDate, formatPrize, getGameColor, getStatusColor, getStatusLabel } from "@/lib/utils";
import type { TournamentSummary } from "@/types/tournament";

interface TournamentCardProps {
  tournament: TournamentSummary;
  className?: string;
}

export function TournamentCard({ tournament, className }: TournamentCardProps) {
  const registrationFull = tournament.registered_teams >= tournament.max_teams;

  return (
    <Link href={`/tournaments/${tournament.id}`}>
      <article
        className={cn(
          "group relative overflow-hidden rounded-xl border border-white/10 bg-white/5",
          "hover:border-white/20 hover:bg-white/10 transition-all duration-200",
          "cursor-pointer",
          className,
        )}
      >
        {/* バナー画像エリア */}
        <div className="relative h-32 bg-gradient-to-br from-brand-900 to-slate-900 overflow-hidden">
          {tournament.banner_url ? (
            <img
              src={tournament.banner_url}
              alt={tournament.name}
              className="h-full w-full object-cover opacity-60 group-hover:opacity-80 transition-opacity"
            />
          ) : (
            <div className="flex h-full items-center justify-center">
              <Trophy className="h-12 w-12 text-white/20" />
            </div>
          )}
          {/* ゲームバッジ */}
          <span
            className={cn(
              "absolute left-3 top-3 rounded-full border px-2.5 py-0.5 text-xs font-semibold",
              getGameColor(tournament.game),
            )}
          >
            {tournament.game}
          </span>
          {/* ステータスバッジ */}
          <span
            className={cn(
              "absolute right-3 top-3 rounded-full px-2.5 py-0.5 text-xs font-semibold",
              getStatusColor(tournament.status),
            )}
          >
            {getStatusLabel(tournament.status)}
          </span>
        </div>

        {/* コンテンツ */}
        <div className="p-4">
          <h3 className="font-bold text-white line-clamp-2 group-hover:text-brand-500 transition-colors">
            {tournament.name}
          </h3>

          <div className="mt-3 space-y-2 text-sm text-slate-400">
            <div className="flex items-center gap-2">
              <Calendar className="h-3.5 w-3.5 flex-shrink-0" />
              <span>{tournament.start_at ? formatDate(tournament.start_at) : "日程未定"}</span>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Users className="h-3.5 w-3.5 flex-shrink-0" />
                <span>
                  <span className={registrationFull ? "text-red-400" : "text-white"}>
                    {tournament.registered_teams}
                  </span>
                  <span> / {tournament.max_teams} チーム</span>
                </span>
              </div>
              {tournament.prize_pool && (
                <span className="font-semibold text-yellow-400">
                  {formatPrize(tournament.prize_pool)}
                </span>
              )}
            </div>
          </div>

          {/* 参加状況バー */}
          <div className="mt-3 h-1.5 rounded-full bg-white/10">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500",
                registrationFull ? "bg-red-500" : "bg-brand-500",
              )}
              style={{
                width: `${Math.min((tournament.registered_teams / tournament.max_teams) * 100, 100)}%`,
              }}
            />
          </div>
        </div>
      </article>
    </Link>
  );
}
