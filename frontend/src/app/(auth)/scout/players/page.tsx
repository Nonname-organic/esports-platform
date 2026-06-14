"use client";

import { useState } from "react";
import Link from "next/link";
import { Users, Filter, Trophy, Star, ChevronRight, Search } from "lucide-react";
import { useScoutPlayers } from "@/features/scout/hooks/use-scout";
import { cn, getGameColor } from "@/lib/utils";
import type { ScoutPlayerCard } from "@/features/scout/api/scout-api";

const GAMES = ["VALORANT", "APEX", "CS2", "LOL", "OVERWATCH"];
const ROLES: Record<string, string[]> = {
  VALORANT: ["Duelist", "Sentinel", "Initiator", "Controller"],
  APEX: ["Assault", "Recon", "Skirmisher", "Support", "Controller"],
  CS2: ["Entry", "AWPer", "Support", "Lurker", "IGL"],
  LOL: ["Top", "Jungle", "Mid", "ADC", "Support"],
  OVERWATCH: ["Tank", "Damage", "Support"],
};
const SORTS = [
  { value: "scout_rating", label: "Scout Rating" },
  { value: "rating", label: "レーティング" },
  { value: "win_rate", label: "勝率" },
  { value: "tournament_count", label: "大会数" },
];

export default function PlayerDiscoveryPage() {
  const [game, setGame] = useState("VALORANT");
  const [role, setRole] = useState("");
  const [region, setRegion] = useState("");
  const [minWinRate, setMinWinRate] = useState("");
  const [lookingOnly, setLookingOnly] = useState(false);
  const [sortBy, setSortBy] = useState("scout_rating");

  const { data: players, isLoading } = useScoutPlayers({
    game,
    role: role || undefined,
    region: region || undefined,
    min_win_rate: minWinRate ? Number(minWinRate) / 100 : undefined,
    looking_only: lookingOnly,
    sort_by: sortBy,
  });

  const roles = ROLES[game] ?? [];

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex items-center gap-3">
        <Link href="/scout" className="text-slate-500 hover:text-white transition-colors">Scout</Link>
        <ChevronRight className="h-4 w-4 text-slate-600" />
        <h1 className="text-xl font-black text-white">Player Discovery</h1>
      </div>

      {/* フィルター */}
      <div className="mb-6 space-y-3 rounded-2xl border border-white/10 bg-slate-900 p-4">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
          <Filter className="h-3.5 w-3.5" />検索条件
        </div>
        <div className="flex flex-wrap gap-2">
          {GAMES.map((g) => (
            <button key={g} onClick={() => { setGame(g); setRole(""); }}
              className={cn("rounded-lg border px-3 py-1.5 text-xs font-bold transition-colors",
                game === g ? "border-brand-500 bg-brand-500/10 text-brand-400" : "border-white/10 text-slate-500 hover:text-white")}>
              {g}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-3">
          <select value={role} onChange={(e) => setRole(e.target.value)}
            className="rounded-lg border border-white/10 bg-slate-800 px-3 py-1.5 text-xs text-white outline-none focus:border-brand-500">
            <option value="">全ロール</option>
            {roles.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <select value={region} onChange={(e) => setRegion(e.target.value)}
            className="rounded-lg border border-white/10 bg-slate-800 px-3 py-1.5 text-xs text-white outline-none focus:border-brand-500">
            <option value="">全リージョン</option>
            {["JP", "KR", "AP", "NA", "EU"].map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <input value={minWinRate} onChange={(e) => setMinWinRate(e.target.value)} type="number" placeholder="最低勝率%"
            className="w-24 rounded-lg border border-white/10 bg-slate-800 px-3 py-1.5 text-xs text-white outline-none focus:border-brand-500" />
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
            <input type="checkbox" checked={lookingOnly} onChange={(e) => setLookingOnly(e.target.checked)}
              className="h-4 w-4 rounded accent-brand-500" />
            募集中のみ
          </label>
          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs text-slate-500">並び替え:</span>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}
              className="rounded-lg border border-white/10 bg-slate-800 px-3 py-1.5 text-xs text-white outline-none focus:border-brand-500">
              {SORTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* 結果 */}
      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-44 animate-pulse rounded-xl bg-white/5" />)}
        </div>
      ) : !players || players.length === 0 ? (
        <div className="flex flex-col items-center py-20 text-center">
          <Users className="mb-3 h-12 w-12 text-slate-700" />
          <p className="text-sm text-slate-500">条件に合うプレイヤーがいません</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {players.map((p) => <PlayerCard key={p.player_id} player={p} />)}
        </div>
      )}
    </div>
  );
}

function PlayerCard({ player }: { player: ScoutPlayerCard }) {
  return (
    <Link
      href={`/players/${player.player_id}`}
      className="rounded-xl border border-white/8 bg-slate-900 p-4 hover:border-brand-500/40 transition-colors"
    >
      <div className="mb-3 flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-slate-800">
          <span className="text-sm font-bold text-slate-400">{player.in_game_name.charAt(0)}</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <p className="truncate font-bold text-white">{player.in_game_name}</p>
            {player.is_looking && <span className="rounded-full bg-green-500/10 px-1.5 py-0.5 text-[9px] font-bold text-green-400">募集中</span>}
          </div>
          <p className="text-xs text-slate-500">{player.main_role ?? "—"} · {player.current_team_name ?? "フリー"}</p>
        </div>
      </div>

      <div className="mb-3 flex items-center gap-1.5">
        <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-bold", getGameColor(player.game))}>{player.game}</span>
        {player.rank && <span className="rounded-full bg-white/5 px-2 py-0.5 text-[10px] text-slate-400">{player.rank}</span>}
      </div>

      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="rounded-lg bg-white/3 py-2">
          <p className="text-sm font-black text-brand-400">{player.scout_rating?.toFixed(0) ?? "—"}</p>
          <p className="text-[9px] text-slate-600">Scout</p>
        </div>
        <div className="rounded-lg bg-white/3 py-2">
          <p className="text-sm font-black text-white">{(player.win_rate * 100).toFixed(0)}%</p>
          <p className="text-[9px] text-slate-600">勝率</p>
        </div>
        <div className="rounded-lg bg-white/3 py-2">
          <p className="text-sm font-black text-yellow-400">{player.championships}</p>
          <p className="text-[9px] text-slate-600">優勝</p>
        </div>
      </div>
    </Link>
  );
}
