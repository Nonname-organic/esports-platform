import { Calendar, Play, Square, Trophy, Clock } from "lucide-react";
import { formatDate } from "@/lib/utils";
import type { MatchDetail } from "@/types/match";

interface TimelineTabProps {
  match: MatchDetail;
}

interface TimelineEvent {
  id: string;
  time: string;
  label: string;
  detail?: string;
  icon: React.ElementType;
  color: string;
}

export function TimelineTab({ match }: TimelineTabProps) {
  const events: TimelineEvent[] = [];

  if (match.scheduled_at) {
    events.push({
      id: "scheduled",
      time: match.scheduled_at,
      label: "試合スケジュール",
      detail: `${match.team1?.name ?? "TBD"} vs ${match.team2?.name ?? "TBD"}`,
      icon: Calendar,
      color: "text-slate-400 bg-slate-400/10",
    });
  }

  if (match.started_at) {
    events.push({
      id: "started",
      time: match.started_at,
      label: "試合開始",
      detail: `${match.format} マッチ開始`,
      icon: Play,
      color: "text-green-400 bg-green-400/10",
    });
  }

  // ゲームイベント
  for (const game of match.games) {
    if (game.winner_id) {
      const winTeam = game.winner_id === match.team1?.id ? match.team1 : match.team2;
      events.push({
        id: `game-${game.game_number}`,
        time: match.started_at ?? match.scheduled_at ?? new Date().toISOString(),
        label: `Game ${game.game_number} 終了`,
        detail: `${match.team1?.tag} ${game.team1_score} - ${game.team2_score} ${match.team2?.tag} | ${winTeam?.name} WIN${game.map_name ? ` (${game.map_name})` : ""}`,
        icon: Trophy,
        color: "text-yellow-400 bg-yellow-400/10",
      });
    }
  }

  if (match.ended_at) {
    const t1Wins = match.games.filter((g) => g.winner_id === match.team1?.id).length;
    const t2Wins = match.games.filter((g) => g.winner_id === match.team2?.id).length;
    const winner = match.winner_id === match.team1?.id ? match.team1 : match.team2;
    events.push({
      id: "ended",
      time: match.ended_at,
      label: "試合終了",
      detail: winner ? `${winner.name} 優勝 (${Math.max(t1Wins, t2Wins)}-${Math.min(t1Wins, t2Wins)})` : "試合終了",
      icon: Square,
      color: "text-brand-400 bg-brand-400/10",
    });
  }

  if (events.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center pt-4">
        <p className="text-sm text-slate-500">タイムラインデータがありません</p>
      </div>
    );
  }

  return (
    <div className="pt-4">
      <ol className="relative border-l border-white/10 space-y-6 pl-6 ml-2">
        {events.map((event) => (
          <li key={event.id} className="relative">
            <span className={`absolute -left-[1.9rem] flex h-8 w-8 items-center justify-center rounded-full ${event.color}`}>
              <event.icon className="h-4 w-4" />
            </span>
            <div className="rounded-lg border border-white/8 bg-slate-900 p-3">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-semibold text-white">{event.label}</p>
                <span className="flex-shrink-0 text-[10px] text-slate-600">
                  <Clock className="inline h-3 w-3 mr-0.5" />
                  {new Date(event.time).toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
              {event.detail && <p className="mt-0.5 text-xs text-slate-400">{event.detail}</p>}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
