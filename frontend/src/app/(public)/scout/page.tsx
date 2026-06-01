"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Users, Shield, Star, Filter } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { cn, getGameColor } from "@/lib/utils";
import type { GameType } from "@/types/tournament";

const GAMES: GameType[] = ["VALORANT", "APEX", "CS2", "LOL", "OVERWATCH"];
const ROLES: Record<string, string[]> = {
  VALORANT: ["Duelist", "Sentinel", "Initiator", "Controller"],
  APEX: ["Assault", "Recon", "Skirmisher", "Support", "Controller"],
  CS2: ["Entry", "AWPer", "Support", "Lurker", "IGL"],
  LOL: ["Top", "Jungle", "Mid", "ADC", "Support"],
  OVERWATCH: ["Tank", "Damage", "Support"],
};

export default function ScoutPage() {
  const [tab, setTab] = useState<"players" | "teams">("players");
  const [game, setGame] = useState<GameType>("VALORANT");
  const [role, setRole] = useState("");
  const [region, setRegion] = useState("");

  const { data: players } = useQuery({
    queryKey: ["scout", "players", game, role, region],
    queryFn: () => apiClient.get<{ data: any[] }>(`/api/v1/scout/players?game=${game}${role ? `&role=${role}` : ""}${region ? `&region=${region}` : ""}`),
    select: (res) => res.data,
  });

  const { data: teams } = useQuery({
    queryKey: ["scout", "teams", game],
    queryFn: () => apiClient.get<{ data: any[] }>(`/api/v1/scout/teams?game=${game}`),
    select: (res) => res.data,
    enabled: tab === "teams",
  });

  const roles = ROLES[game] ?? [];

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* ヘッダー */}
      <div className="mb-8">
        <h1 className="text-3xl font-black text-white">Scout Platform</h1>
        <p className="mt-1 text-slate-400">プレイヤーを探す・チームを探す</p>
      </div>

      {/* タブ */}
      <div className="mb-6 flex gap-2">
        <button onClick={() => setTab("players")}
          className={cn("flex items-center gap-2 rounded-xl border px-5 py-2.5 text-sm font-bold transition-colors",
            tab === "players" ? "border-brand-500 bg-brand-500/10 text-brand-400" : "border-white/10 text-slate-400 hover:text-white")}>
          <Users className="h-4 w-4" />プレイヤーを探す
        </button>
        <button onClick={() => setTab("teams")}
          className={cn("flex items-center gap-2 rounded-xl border px-5 py-2.5 text-sm font-bold transition-colors",
            tab === "teams" ? "border-brand-500 bg-brand-500/10 text-brand-400" : "border-white/10 text-slate-400 hover:text-white")}>
          <Shield className="h-4 w-4" />チームを探す
        </button>
      </div>

      {/* フィルター */}
      <div className="mb-6 flex flex-wrap items-center gap-3 rounded-xl border border-white/10 bg-slate-900 p-4">
        <Filter className="h-4 w-4 text-slate-500" />

        {/* ゲーム */}
        <div className="flex gap-1">
          {GAMES.map((g) => (
            <button key={g} onClick={() => { setGame(g); setRole(""); }}
              className={cn("rounded-lg border px-3 py-1.5 text-xs font-bold transition-colors",
                game === g ? "border-brand-500 bg-brand-500/10 text-brand-400" : "border-white/10 text-slate-500 hover:text-white")}>
              {g}
            </button>
          ))}
        </div>

        {/* ロール */}
        {roles.length > 0 && (
          <select value={role} onChange={(e) => setRole(e.target.value)}
            className="rounded-lg border border-white/10 bg-slate-800 px-3 py-1.5 text-xs text-white outline-none focus:border-brand-500">
            <option value="">全ロール</option>
            {roles.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        )}

        {/* リージョン */}
        <select value={region} onChange={(e) => setRegion(e.target.value)}
          className="rounded-lg border border-white/10 bg-slate-800 px-3 py-1.5 text-xs text-white outline-none focus:border-brand-500">
          <option value="">全リージョン</option>
          {["JP", "KR", "AP", "NA", "EU"].map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
      </div>

      {/* プレイヤー一覧 */}
      {tab === "players" && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {(players ?? []).length === 0 ? (
            <div className="col-span-full flex h-48 flex-col items-center justify-center rounded-xl border border-white/10 bg-slate-900">
              <Users className="mb-3 h-10 w-10 text-slate-700" />
              <p className="text-sm text-slate-500">プレイヤーがいません</p>
            </div>
          ) : (
            (players ?? []).map((p: any) => (
              <div key={p.id} className="rounded-xl border border-white/8 bg-slate-900 p-4 hover:border-white/15 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full border border-white/10 bg-slate-800 flex items-center justify-center">
                    <span className="text-sm font-bold text-slate-400">
                      {(p.in_game_name ?? "?").charAt(0)}
                    </span>
                  </div>
                  <div>
                    <p className="font-bold text-white">{p.in_game_name}</p>
                    <p className="text-xs text-slate-500">{p.main_role ?? "—"} · {p.region ?? "—"}</p>
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-2">
                  <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-bold", getGameColor(p.game))}>
                    {p.game}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* チーム一覧 */}
      {tab === "teams" && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {(teams ?? []).length === 0 ? (
            <div className="col-span-full flex h-48 flex-col items-center justify-center rounded-xl border border-white/10 bg-slate-900">
              <Shield className="mb-3 h-10 w-10 text-slate-700" />
              <p className="text-sm text-slate-500">チームがいません</p>
            </div>
          ) : (
            (teams ?? []).map((t: any) => (
              <div key={t.id} className="rounded-xl border border-white/8 bg-slate-900 p-4">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 overflow-hidden rounded-lg border border-white/10 bg-slate-800 flex items-center justify-center">
                    {t.logo_url ? <img src={t.logo_url} alt="" className="h-full w-full object-contain" /> :
                      <span className="text-xs font-bold text-slate-500">{t.tag}</span>}
                  </div>
                  <div>
                    <p className="font-bold text-white">{t.name}</p>
                    <p className="text-xs text-slate-500">[{t.tag}]</p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
