import { Map, Clock, Trophy } from "lucide-react";
import { cn, formatDate } from "@/lib/utils";
import type { MatchDetail } from "@/types/match";

interface OverviewTabProps {
  match: MatchDetail;
}

export function OverviewTab({ match }: OverviewTabProps) {
  const team1Wins = match.games.filter((g) => g.winner_id === match.team1?.id).length;
  const team2Wins = match.games.filter((g) => g.winner_id === match.team2?.id).length;

  return (
    <div className="space-y-4 pt-4">
      {/* マップ別スコア */}
      {match.games.length > 0 && (
        <section className="rounded-xl border border-white/10 bg-slate-900">
          <div className="border-b border-white/10 px-5 py-3">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Map className="h-4 w-4 text-brand-400" />
              マップ別結果
            </h2>
          </div>
          <div className="divide-y divide-white/5">
            {match.games.map((game) => {
              const t1Win = game.winner_id === match.team1?.id;
              const t2Win = game.winner_id === match.team2?.id;
              const isOngoing = !game.winner_id && match.status === "ongoing";
              const dur = game.duration_seconds
                ? `${Math.floor(game.duration_seconds / 60)}:${String(game.duration_seconds % 60).padStart(2, "0")}`
                : null;

              return (
                <div key={game.id} className="grid grid-cols-[1fr_auto_1fr] items-center gap-4 px-5 py-4">
                  {/* Team 1 side */}
                  <div className="flex items-center gap-3">
                    <span className={cn(
                      "text-2xl font-black tabular-nums",
                      t1Win ? "text-green-400" : t2Win ? "text-red-400/60" : "text-white",
                    )}>
                      {game.team1_score}
                    </span>
                    {t1Win && <Trophy className="h-4 w-4 text-yellow-400" />}
                  </div>

                  {/* Map info */}
                  <div className="text-center">
                    <p className="text-sm font-bold text-white">{game.map_name ?? `Map ${game.game_number}`}</p>
                    {dur && <p className="text-xs text-slate-500">{dur}</p>}
                    {isOngoing && <p className="text-xs text-red-400 animate-pulse">進行中</p>}
                  </div>

                  {/* Team 2 side */}
                  <div className="flex items-center justify-end gap-3">
                    {t2Win && <Trophy className="h-4 w-4 text-yellow-400" />}
                    <span className={cn(
                      "text-2xl font-black tabular-nums",
                      t2Win ? "text-green-400" : t1Win ? "text-red-400/60" : "text-white",
                    )}>
                      {game.team2_score}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* 試合情報 */}
      <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <h2 className="mb-4 text-sm font-bold text-white">試合情報</h2>
        <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
          {[
            { label: "フォーマット", value: match.format },
            { label: "ラウンド", value: `Round ${match.round_number}` },
            { label: "ステータス", value: match.status },
            ...(match.scheduled_at ? [{ label: "予定時刻", value: formatDate(match.scheduled_at) }] : []),
            ...(match.started_at ? [{ label: "開始時刻", value: formatDate(match.started_at) }] : []),
            ...(match.ended_at ? [{ label: "終了時刻", value: formatDate(match.ended_at) }] : []),
          ].map(({ label, value }) => (
            <div key={label}>
              <dt className="text-slate-500">{label}</dt>
              <dd className="mt-0.5 font-semibold text-white">{value}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}
