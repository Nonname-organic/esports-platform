import Link from "next/link";
import { Calendar, Clock, Users, Trophy, Zap } from "lucide-react";
import { cn, formatPrize, getGameColor, getStatusColor, getStatusLabel } from "@/lib/utils";
import type { TournamentSummary } from "@/types/tournament";

function fmtShort(iso: string | null): string {
  if (!iso) return "未定";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "未定";
  return d.toLocaleDateString("ja-JP", { month: "numeric", day: "numeric" });
}
function period(a: string | null, b: string | null): string {
  if (!a && !b) return "未定";
  return `${fmtShort(a)} 〜 ${fmtShort(b)}`;
}

interface TournamentCardProps {
  tournament: TournamentSummary;
  className?: string;
}

export function TournamentCard({ tournament, className }: TournamentCardProps) {
  const fillRate = Math.min((tournament.registered_teams / tournament.max_teams) * 100, 100);
  const isFull = tournament.registered_teams >= tournament.max_teams;
  const isOngoing = tournament.status === "ongoing";

  return (
    <Link href={`/tournaments/${tournament.id}`} className="group block focus:outline-none">
      <article
        className={cn(
          "relative overflow-hidden rounded-xl border border-white/10 bg-slate-900",
          "transition-all duration-200",
          "hover:border-brand-500/40 hover:shadow-lg hover:shadow-brand-500/5",
          "focus-within:border-brand-500/40",
          className,
        )}
      >
        {/* バナー */}
        <div className="relative h-36 overflow-hidden bg-gradient-to-br from-slate-800 to-slate-900">
          {tournament.banner_url ? (
            <img
              src={tournament.banner_url}
              alt={tournament.name}
              className="h-full w-full object-cover opacity-50 transition-opacity duration-300 group-hover:opacity-70"
            />
          ) : (
            <div className="flex h-full items-center justify-center">
              <Trophy className="h-14 w-14 text-white/10" />
            </div>
          )}

          {/* グラデーションオーバーレイ */}
          <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 via-transparent to-transparent" />

          {/* ゲームバッジ */}
          <span
            className={cn(
              "absolute left-3 top-3 rounded-full border px-2.5 py-0.5 text-xs font-bold tracking-wide",
              getGameColor(tournament.game),
            )}
          >
            {tournament.game}
          </span>

          {/* ステータスバッジ */}
          <span
            className={cn(
              "absolute right-3 top-3 inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold",
              getStatusColor(tournament.status),
            )}
          >
            {isOngoing && <Zap className="h-3 w-3" />}
            {getStatusLabel(tournament.status)}
          </span>
        </div>

        {/* コンテンツ */}
        <div className="p-4">
          <h3 className="line-clamp-2 font-bold text-white transition-colors group-hover:text-brand-400">
            {tournament.name}
          </h3>

          <div className="mt-3 space-y-1.5 text-sm text-slate-400">
            {/* 申込受付期間（参加できるか一目で分かるよう、受付中は緑で強調） */}
            <div className="flex items-center gap-2">
              <Clock className="h-3.5 w-3.5 flex-shrink-0 text-slate-500" />
              <span className="w-8 flex-shrink-0 text-slate-500">受付</span>
              <span className={cn(tournament.status === "registration_open" ? "font-semibold text-green-400" : "text-slate-300")}>
                {period(tournament.registration_start_at, tournament.registration_end_at)}
              </span>
              {tournament.status === "registration_open" && (
                <span className="rounded bg-green-500/15 px-1.5 py-0.5 text-[10px] font-bold text-green-400">受付中</span>
              )}
            </div>

            {/* 開催期間 */}
            <div className="flex items-center gap-2">
              <Calendar className="h-3.5 w-3.5 flex-shrink-0 text-slate-500" />
              <span className="w-8 flex-shrink-0 text-slate-500">開催</span>
              <span className="text-slate-300">{period(tournament.start_at, tournament.end_at)}</span>
            </div>

            <div className="flex items-center justify-between pt-0.5">
              <div className="flex items-center gap-2">
                <Users className="h-3.5 w-3.5 flex-shrink-0 text-slate-500" />
                <span>
                  <span className={cn("font-semibold", isFull ? "text-red-400" : "text-white")}>
                    {tournament.registered_teams}
                  </span>
                  <span className="text-slate-500"> / {tournament.max_teams} チーム</span>
                </span>
              </div>

              {tournament.prize_pool != null && tournament.prize_pool > 0 && (
                <span className="font-semibold text-yellow-400">
                  {formatPrize(tournament.prize_pool)}
                </span>
              )}
            </div>
          </div>

          {/* 参加状況バー */}
          <div className="mt-3 h-1 rounded-full bg-white/10">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500",
                isFull ? "bg-red-500" : "bg-brand-500",
              )}
              style={{ width: `${fillRate}%` }}
              role="progressbar"
              aria-valuenow={tournament.registered_teams}
              aria-valuemax={tournament.max_teams}
            />
          </div>
        </div>
      </article>
    </Link>
  );
}
