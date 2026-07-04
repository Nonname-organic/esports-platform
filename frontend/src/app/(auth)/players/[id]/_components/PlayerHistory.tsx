"use client";

import { Trophy, Users, Shield } from "lucide-react";
import Link from "next/link";
import { usePlayerAchievements } from "@/features/career/hooks/use-career";
import type { Player } from "@/types/player";
import { TournamentTable, type TournamentRow } from "./shared/tournament-table";
import { EmptyState } from "./shared/empty-state";
import { PlayerActivity } from "./PlayerActivity";

interface Props {
  player: Player;
  playerId: string;
}

export function PlayerHistory({ player, playerId }: Props) {
  const { data: achievements, isLoading: achLoading } = usePlayerAchievements(playerId);

  const tournamentRows: TournamentRow[] = (achievements ?? []).map((a) => ({
    id: a.id,
    name: a.title,
    placement: a.type === "champion" ? "優勝" : a.type === "top4" ? "TOP4" : a.description ?? null,
    date: a.earned_at,
    href: a.tournament_id ? `/tournaments/${a.tournament_id}` : undefined,
  }));

  return (
    <div className="space-y-8 pt-6">
      {/* 最近の活動（公開イベント / Activity Feed） */}
      <PlayerActivity playerId={playerId} />

      {/* 大会履歴 */}
      <section>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
          <Trophy className="h-4 w-4 text-yellow-400" /> Tournament History
        </h2>
        {achLoading ? (
          <div className="h-40 animate-pulse rounded-xl bg-white/5" />
        ) : tournamentRows.length > 0 ? (
          <TournamentTable rows={tournamentRows} />
        ) : (
          <EmptyState icon={Trophy} title="大会履歴がありません" desc="大会参加後に表示されます。" />
        )}
      </section>

      {/* 所属チーム履歴 */}
      <section>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
          <Users className="h-4 w-4 text-brand-400" /> Team History
        </h2>
        {player.team_id ? (
          <Link href={`/teams/${player.team_id}`}
            className="flex items-center gap-4 rounded-xl border border-white/10 bg-slate-900 p-4 hover:border-brand-500/40 transition-colors">
            <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center overflow-hidden rounded-xl border border-white/10 bg-slate-800">
              {player.team_logo_url ? <img src={player.team_logo_url} alt="" className="h-full w-full object-contain" /> : <Shield className="h-6 w-6 text-slate-600" />}
            </div>
            <div className="flex-1">
              <p className="text-sm font-bold text-white">{player.team_name} {player.team_tag && <span className="text-slate-500">[{player.team_tag}]</span>}</p>
              <p className="text-xs text-slate-500">現在所属中</p>
            </div>
          </Link>
        ) : (
          <EmptyState icon={Users} title="所属チーム履歴がありません" desc="チームに加入すると履歴が表示されます。" />
        )}
      </section>
    </div>
  );
}
