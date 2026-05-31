import { cn } from "@/lib/utils";
import type { MatchDetail, MatchGame, PlayerStat } from "@/types/match";

interface MapsTabProps {
  match: MatchDetail;
}

export function MapsTab({ match }: MapsTabProps) {
  if (match.games.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center pt-4">
        <p className="text-sm text-slate-500">マップデータがまだありません</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 pt-4">
      {match.games.map((game) => (
        <GameDetail key={game.id} game={game} match={match} />
      ))}
    </div>
  );
}

function GameDetail({ game, match }: { game: MatchGame; match: MatchDetail }) {
  const t1Players = game.player_stats.filter((p) => p.team_id === match.team1?.id);
  const t2Players = game.player_stats.filter((p) => p.team_id === match.team2?.id);
  const t1Win = game.winner_id === match.team1?.id;
  const t2Win = game.winner_id === match.team2?.id;
  const dur = game.duration_seconds
    ? `${Math.floor(game.duration_seconds / 60)}:${String(game.duration_seconds % 60).padStart(2, "0")}`
    : "進行中";

  return (
    <div className="overflow-hidden rounded-xl border border-white/10 bg-slate-900">
      {/* ヘッダー */}
      <div className="flex items-center justify-between border-b border-white/10 bg-white/3 px-5 py-3">
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold text-white">{game.map_name ?? `Map ${game.game_number}`}</span>
          <span className="text-xs text-slate-500">Game {game.game_number}</span>
        </div>
        <span className="text-xs text-slate-500">{dur}</span>
      </div>

      {/* スコア行 */}
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4 px-5 py-4">
        <div className="flex items-center gap-2">
          <span className={cn("text-3xl font-black", t1Win ? "text-green-400" : t2Win ? "text-slate-500" : "text-white")}>
            {game.team1_score}
          </span>
          <span className="text-xs font-bold text-slate-400">{match.team1?.tag}</span>
          {t1Win && <span className="ml-auto rounded-full bg-green-500/10 px-2 py-0.5 text-[10px] font-bold text-green-400">WIN</span>}
        </div>
        <span className="text-slate-600">—</span>
        <div className="flex items-center justify-end gap-2">
          {t2Win && <span className="mr-auto rounded-full bg-green-500/10 px-2 py-0.5 text-[10px] font-bold text-green-400">WIN</span>}
          <span className="text-xs font-bold text-slate-400">{match.team2?.tag}</span>
          <span className={cn("text-3xl font-black", t2Win ? "text-green-400" : t1Win ? "text-slate-500" : "text-white")}>
            {game.team2_score}
          </span>
        </div>
      </div>

      {/* プレイヤースタッツ */}
      {game.player_stats.length > 0 && (
        <div className="border-t border-white/10 px-5 pb-5 pt-3">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <PlayerStatsTable players={t1Players} teamName={match.team1?.name ?? "Team 1"} isWin={t1Win} />
            <PlayerStatsTable players={t2Players} teamName={match.team2?.name ?? "Team 2"} isWin={t2Win} />
          </div>
        </div>
      )}
    </div>
  );
}

function PlayerStatsTable({ players, teamName, isWin }: {
  players: PlayerStat[]; teamName: string; isWin: boolean;
}) {
  const sorted = [...players].sort((a, b) => b.score - a.score);

  return (
    <div>
      <div className={cn("mb-2 flex items-center gap-2")}>
        <span className="text-xs font-bold text-slate-400">{teamName}</span>
        {isWin && <span className="rounded-full bg-green-500/10 px-1.5 py-0.5 text-[9px] font-bold text-green-400">WIN</span>}
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-white/8 text-slate-500">
            <th className="pb-1.5 text-left font-medium">プレイヤー</th>
            <th className="pb-1.5 text-center font-medium w-8">K</th>
            <th className="pb-1.5 text-center font-medium w-8">D</th>
            <th className="pb-1.5 text-center font-medium w-8">A</th>
            <th className="pb-1.5 text-right font-medium">KDA</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {sorted.map((p, i) => {
            const kda = ((p.kills + p.assists) / Math.max(p.deaths, 1)).toFixed(2);
            return (
              <tr key={p.player_id} className={i === 0 ? "bg-yellow-500/3" : ""}>
                <td className="py-1.5">
                  <div className="flex items-center gap-1.5">
                    {p.agent && (
                      <span className="rounded bg-white/5 px-1 text-[9px] text-slate-400">{p.agent.slice(0, 4)}</span>
                    )}
                    <span className="truncate text-slate-300 max-w-[80px]">{p.player_name}</span>
                  </div>
                </td>
                <td className="py-1.5 text-center font-semibold text-green-400">{p.kills}</td>
                <td className="py-1.5 text-center font-semibold text-red-400">{p.deaths}</td>
                <td className="py-1.5 text-center font-semibold text-blue-400">{p.assists}</td>
                <td className="py-1.5 text-right font-bold text-white">{kda}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
