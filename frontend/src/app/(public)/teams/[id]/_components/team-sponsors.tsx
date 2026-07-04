"use client";

import { Award } from "lucide-react";
import { useSponsors } from "@/features/sponsors/hooks/use-sponsors";

export function TeamSponsors({ teamId }: { teamId: string }) {
  const { data: sponsors } = useSponsors(teamId);
  if (!sponsors || sponsors.length === 0) return null;

  return (
    <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
      <h2 className="mb-4 flex items-center gap-2 text-sm font-bold text-white">
        <Award className="h-4 w-4 text-brand-400" /> スポンサー
      </h2>
      <div className="flex flex-wrap gap-3">
        {sponsors.map((s) => {
          const inner = (
            <div className="flex items-center gap-2.5 rounded-xl border border-white/10 bg-white/3 px-3 py-2 transition-colors hover:border-white/20">
              <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-slate-800">
                {s.logo_url ? <img src={s.logo_url} alt={s.name} className="h-full w-full object-contain" /> : <span className="text-[10px] font-bold text-slate-500">{s.name.slice(0, 2)}</span>}
              </div>
              <div>
                <p className="text-sm font-semibold text-white">{s.name}</p>
                {s.sponsor_type && <p className="text-[10px] uppercase tracking-wide text-slate-500">{s.sponsor_type}</p>}
              </div>
            </div>
          );
          return s.url ? (
            <a key={s.id} href={s.url} target="_blank" rel="noopener noreferrer">{inner}</a>
          ) : (
            <div key={s.id}>{inner}</div>
          );
        })}
      </div>
    </section>
  );
}
