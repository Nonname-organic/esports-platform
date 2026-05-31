import { Trophy, Star, Users, Swords } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MatchDetail, PlayerStat } from "@/types/match";

interface MatchResultProps {
  match: MatchDetail;
}

interface AggregatedStat {
  player_id: string;
  player_name: string;
  team_id: string;
  kills: number;
  deaths: number;
  assists: number;
  score: number;
  first_bloods: number;
  games: number;
  agent: string | null;
  kda: number;
}

function getAggregatedStats(match: MatchDetail): AggregatedStat[] {
  const map = new Map<string, AggregatedStat>();
  for (const game of match.games) {
    for (const p of game.player_stats) {
      const ex = map.get(p.player_id);
      if (ex) {
        ex.kills += p.kills;
        ex.deaths += p.deaths;
        ex.assists += p.assists;
        ex.score += p.score;
        ex.first_bloods += p.first_bloods;
        ex.games += 1;
      } else {
        map.set(p.player_id, { ...p, games: 1, kda: 0 });
      }
    }
  }
  return Array.from(map.values()).map((p) => ({
    ...p,
    kda: (p.kills + p.assists) / Math.max(p.deaths, 1),
  }));
}

export function MatchResult({ match }: MatchResultProps) {
  if (match.status !== "completed") return null;

  const allStats = getAggregatedStats(match);
  const winnerTeam = match.winner_id === match.team1?.id ? match.team1 : match.team2;
  const loserTeam = match.winner_id === match.team1?.id ? match.team2 : match.team1;

  // MVP: 勝利チームで最高KDA
  const winnerStats = allStats.filter((p) => p.team_id === match.winner_id);
  const mvp = winnerStats.sort((a, b) => b.kda - a.kda)[0];

  // チームスタッツ集計
  const t1Stats = allStats.filter((p) => p.team_id === match.team1?.id);
  const t2Stats = allStats.filter((p) => p.team_id === match.team2?.id);
  const sum = (arr: AggregatedStat[], key: keyof AggregatedStat) =>
    arr.reduce((s, p) => s + (p[key] as number), 0);

  const t1Wins = match.games.filter((g) => g.winner_id === match.team1?.id).length;
  const t2Wins = match.games.filter((g) => g.winner_id === match.team2?.id).length;

  return (
    <div className="space-y-5">
      {/* MVP */}
      {mvp && (
        <section className="overflow-hidden rounded-2xl border border-yellow-500/30 bg-gradient-to-br from-yellow-500/10 to-slate-900">
          <div className="border-b border-yellow-500/20 px-5 py-3 flex items-center gap-2">
            <Star className="h-4 w-4 text-yellow-400" fill="currentColor" />
            <h2 className="text-sm font-bold text-yellow-400">MVP</h2>
          </div>
          <div className="flex items-center gap-5 px-5 py-5">
            <div className="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-2xl border border-yellow-500/30 bg-yellow-500/10">
              <Trophy className="h-8 w-8 text-yellow-400" />
            </div>
            <div>
              <p className="text-xl font-black text-white">{mvp.player_name}</p>
              {mvp.agent && <p className="text-sm text-slate-400">{mvp.agent}</p>}
              <div className="mt-2 flex items-center gap-4 text-sm">
                <span className="text-green-400 font-semibold">{mvp.kills}K</span>
                <span className="text-red-400 font-semibold">{mvp.deaths}D</span>
                <span className="text-blue-400 font-semibold">{mvp.assists}A</span>
                <span className="font-black text-yellow-400">{mvp.kda.toFixed(2)} KDA</span>
              </div>
            </div>
            <div className="ml-auto text-right">
              <p className="text-3xl font-black text-yellow-400">{mvp.kda.toFixed(2)}</p>
              <p className="text-xs text-slate-500">KDA</p>
            </div>
          </div>
        </section>
      )}

      {/* マッチサマリー */}
      <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-bold text-white">
          <Swords className="h-4 w-4 text-brand-400" />
          マッチサマリー
        </h2>

        {/* 最終スコア */}
        <div className="mb-4 flex items-center justify-center gap-6 rounded-xl bg-white/3 py-4">
          <div className="text-center">
            <p className={cn("text-sm font-bold", match.winner_id === match.team1?.id ? "text-yellow-400" : "text-slate-400")}>
              {match.team1?.name ?? "Team 1"}
              {match.winner_id === match.team1?.id && " 🏆"}
            </p>
          </div>
          <div className="text-center">
            <p className="text-4xl font-black tabular-nums text-white">
              {t1Wins} : {t2Wins}
            </p>
            <p className="text-xs text-slate-500 mt-1">{match.format}</p>
          </div>
          <div className="text-center">
            <p className={cn("text-sm font-bold", match.winner_id === match.team2?.id ? "text-yellow-400" : "text-slate-400")}>
              {match.winner_id === match.team2?.id && "🏆 "}
              {match.team2?.name ?? "Team 2"}
            </p>
          </div>
        </div>

        {/* ゲーム別サマリー */}
        <div className="space-y-1.5">
          {match.games.map((game) => (
            <div key={game.id} className="flex items-center justify-between rounded-lg bg-white/3 px-4 py-2.5 text-sm">
              <span className="font-semibold text-slate-300">{game.map_name ?? `Map ${game.game_number}`}</span>
              <span className="tabular-nums font-bold text-white">
                <span className={game.winner_id === match.team1?.id ? "text-green-400" : ""}>{game.team1_score}</span>
                <span className="mx-2 text-slate-600">—</span>
                <span className={game.winner_id === match.team2?.id ? "text-green-400" : ""}>{game.team2_score}</span>
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* チームスタッツ */}
      <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-bold text-white">
          <Users className="h-4 w-4 text-brand-400" />
          チームスタッツ比較
        </h2>
        <div className="space-y-3">
          {[
            { label: "Total Kills", t1: sum(t1Stats, "kills"), t2: sum(t2Stats, "kills") },
            { label: "Total Deaths", t1: sum(t1Stats, "deaths"), t2: sum(t2Stats, "deaths") },
            { label: "Total Assists", t1: sum(t1Stats, "assists"), t2: sum(t2Stats, "assists") },
            { label: "First Bloods", t1: sum(t1Stats, "first_bloods"), t2: sum(t2Stats, "first_bloods") },
          ].map(({ label, t1, t2 }) => {
            const total = t1 + t2 || 1;
            const t1Pct = (t1 / total) * 100;
            return (
              <div key={label}>
                <div className="mb-1 flex justify-between text-xs text-slate-500">
                  <span className="font-semibold text-white">{t1}</span>
                  <span>{label}</span>
                  <span className="font-semibold text-white">{t2}</span>
                </div>
                <div className="flex h-2 overflow-hidden rounded-full">
                  <div className="bg-brand-500" style={{ width: `${t1Pct}%` }} />
                  <div className="bg-red-500/70 flex-1" />
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
