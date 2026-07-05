"use client";

import { ResultsCard } from "./results-card";
import { LiveStatusCard } from "./live-status-card";
import { StreamCard } from "./stream-card";
import { LiveTicker } from "./live-ticker";
import { UpcomingCard } from "./upcoming-card";
import { TournamentStatisticsCard } from "./statistics-card";

/**
 * 没入型大会詳細の Widget 群を合成（各Widgetは独立・自分のRead Modelのみ参照）。
 * Live系は open な大会でのみポーリング（Visibility対応・WS/SSE差し替え可）。
 */
export function TournamentImmersion({ tournamentId, status }: { tournamentId: string; status: string }) {
  const live = ["registration_closed", "check_in", "ongoing"].includes(status);
  const completed = status === "completed";

  return (
    <div className="space-y-6">
      {completed && <ResultsCard tournamentId={tournamentId} />}
      {live && <LiveStatusCard tournamentId={tournamentId} active={live} />}
      <StreamCard tournamentId={tournamentId} />
      {live && <LiveTicker tournamentId={tournamentId} active={live} />}
      {live && <UpcomingCard tournamentId={tournamentId} active={live} />}
      <TournamentStatisticsCard tournamentId={tournamentId} />
    </div>
  );
}
