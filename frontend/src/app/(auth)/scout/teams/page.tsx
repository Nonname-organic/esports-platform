"use client";

import { useState } from "react";
import Link from "next/link";
import { Shield, Filter, ChevronRight, Users, Trophy } from "lucide-react";
import { useScoutTeams } from "@/features/scout/hooks/use-scout";
import { cn, getGameColor } from "@/lib/utils";
import type { ScoutTeamCard } from "@/features/scout/api/scout-api";

const GAMES = ["VALORANT", "APEX", "CS2", "LOL", "OVERWATCH"];

export default function TeamDiscoveryPage() {
  const [game, setGame] = useState("VALORANT");
  const [region, setRegion] = useState("");
  const [recruitingOnly, setRecruitingOnly] = useState(false);

  const { data: teams, isLoading } = useScoutTeams({
    game, region: region || undefined, recruiting_only: recruitingOnly,
  });

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex items-center gap-3">
        <Link href="/scout" className="text-slate-500 hover:text-white transition-colors">Scout</Link>
        <ChevronRight className="h-4 w-4 text-slate-600" />
        <h1 className="text-xl font-black text-white">Team Discovery</h1>
      </div>

      <div className="mb-6 space-y-3 rounded-2xl border border-white/10 bg-slate-900 p-4">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
          <Filter className="h-3.5 w-3.5" />検索条件
        </div>
        <div className="flex flex-wrap gap-2">
          {GAMES.map((g) => (
            <button key={g} onClick={() => setGame(g)}
              className={cn("rounded-lg border px-3 py-1.5 text-xs font-bold transition-colors",
                game === g ? "border-brand-500 bg-brand-500/10 text-brand-400" : "border-white/10 text-slate-500 hover:text-white")}>
              {g}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <select value={region} onChange={(e) => setRegion(e.target.value)}
            className="rounded-lg border border-white/10 bg-slate-800 px-3 py-1.5 text-xs text-white outline-none focus:border-brand-500">
            <option value="">全リージョン</option>
            {["JP", "KR", "AP", "NA", "EU"].map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
            <input type="checkbox" checked={recruitingOnly} onChange={(e) => setRecruitingOnly(e.target.checked)}
              className="h-4 w-4 rounded accent-brand-500" />
            募集中のみ
          </label>
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-40 animate-pulse rounded-xl bg-white/5" />)}
        </div>
      ) : !teams || teams.length === 0 ? (
        <div className="flex flex-col items-center py-20 text-center">
          <Shield className="mb-3 h-12 w-12 text-slate-700" />
          <p className="text-sm text-slate-500">条件に合うチームがいません</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {teams.map((t) => <TeamCard key={t.team_id} team={t} />)}
        </div>
      )}
    </div>
  );
}

function TeamCard({ team }: { team: ScoutTeamCard }) {
  return (
    <Link href={`/teams/${team.team_id}`}
      className="rounded-xl border border-white/8 bg-slate-900 p-4 hover:border-brand-500/40 transition-colors">
      <div className="mb-3 flex items-center gap-3">
        <div className="h-11 w-11 overflow-hidden rounded-lg border border-white/10 bg-slate-800 flex items-center justify-center">
          {team.logo_url ? <img src={team.logo_url} alt="" className="h-full w-full object-contain" /> :
            <span className="text-xs font-bold text-slate-500">{team.tag.slice(0, 3)}</span>}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <p className="truncate font-bold text-white">{team.name}</p>
            {team.is_recruiting && <span className="rounded-full bg-green-500/10 px-1.5 py-0.5 text-[9px] font-bold text-green-400">募集中</span>}
          </div>
          <p className="text-xs text-slate-500">[{team.tag}] · {team.region ?? "—"}</p>
        </div>
      </div>
      <div className="mb-3">
        <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-bold", getGameColor(team.game))}>{team.game}</span>
      </div>
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="rounded-lg bg-white/3 py-2">
          <p className="text-sm font-black text-brand-400">{team.avg_rating?.toFixed(0) ?? "—"}</p>
          <p className="text-[9px] text-slate-600">Rating</p>
        </div>
        <div className="rounded-lg bg-white/3 py-2">
          <p className="text-sm font-black text-white">{(team.win_rate * 100).toFixed(0)}%</p>
          <p className="text-[9px] text-slate-600">勝率</p>
        </div>
        <div className="rounded-lg bg-white/3 py-2">
          <p className="text-sm font-black text-slate-300">{team.roster_count}</p>
          <p className="text-[9px] text-slate-600">人数</p>
        </div>
      </div>
    </Link>
  );
}
