"use client";

import Link from "next/link";
import { CalendarClock } from "lucide-react";
import { useTournamentLive } from "@/features/tournament-live/hooks/use-tournament-live";
import { Countdown } from "@/components/live/countdown";

/** Upcoming Matches: 次の試合を Countdown 付きで表示。 */
export function UpcomingCard({ tournamentId, active }: { tournamentId: string; active: boolean }) {
  const { data } = useTournamentLive(tournamentId, active);
  const upcoming = data?.upcoming ?? [];
  if (upcoming.length === 0) return null;

  return (
    <section className="rounded-2xl border border-white/10 bg-slate-900 p-5">
      <h2 className="mb-3 flex items-center gap-2 font-bold text-white">
        <CalendarClock className="h-4 w-4 text-brand-400" /> Upcoming
      </h2>
      <ul className="space-y-2.5">
        {upcoming.map((m) => (
          <li key={m.id}>
            <Link href={`/matches/${m.id}`} className="flex items-center gap-3 rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2.5 transition-colors hover:border-white/20 hover:bg-white/[0.04]">
              <span className="min-w-0 flex-1 truncate text-sm font-semibold text-white">
                {m.team1?.name ?? "TBD"} <span className="text-slate-600">vs</span> {m.team2?.name ?? "TBD"}
              </span>
              {m.scheduled_at ? (
                <span className="flex-shrink-0">
                  <span className="mb-0.5 block text-right text-[9px] font-bold uppercase tracking-wider text-slate-500">Starts in</span>
                  <Countdown target={m.scheduled_at} size="md" />
                </span>
              ) : (
                <span className="flex-shrink-0 text-xs text-slate-500">日程未定</span>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
