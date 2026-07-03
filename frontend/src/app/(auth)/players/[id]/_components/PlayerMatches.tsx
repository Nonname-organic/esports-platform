"use client";

import { useMemo, useState } from "react";
import { Swords, Search } from "lucide-react";
import { useCompetitive } from "@/features/riot/hooks/use-riot";
import { usePlayerMatchHistory } from "@/features/players/hooks/use-player";
import { SourceToggle, type StatSource } from "./shared/source-toggle";
import { MatchTable, type MatchRow } from "./shared/match-table";
import { EmptyState } from "./shared/empty-state";

type ResultFilter = "all" | "win" | "loss";

const sel = "rounded-lg border border-white/10 bg-slate-800 px-3 py-1.5 text-xs text-white outline-none focus:border-brand-500";

export function PlayerMatches({ playerId }: { playerId: string }) {
  const [source, setSource] = useState<StatSource>("competitive");
  const [mapFilter, setMapFilter] = useState("");
  const [agentFilter, setAgentFilter] = useState("");
  const [resultFilter, setResultFilter] = useState<ResultFilter>("all");

  const { data: comp, isLoading: compLoading } = useCompetitive(playerId);
  const { data: history, isLoading: histLoading } = usePlayerMatchHistory(playerId);

  const isLoading = source === "competitive" ? compLoading : histLoading;

  // 元データ（ソース別）
  const rawRows: MatchRow[] = useMemo(() => {
    if (source === "competitive") {
      return (comp?.matches ?? []).map((m) => ({
        id: m.match_id, agent: m.agent, map_name: m.map_name, won: m.won,
        kills: m.kills, deaths: m.deaths, assists: m.assists,
        kd: m.kd, kda: m.kda, acs: m.acs, adr: m.adr, hs_rate: m.hs_rate, played_at: m.played_at,
      }));
    }
    return (history?.data ?? []).map((m) => ({
      id: m.id,
      agent: m.agent, map_name: m.map_name,
      won: m.result === "win" ? true : m.result === "loss" ? false : null,
      kills: m.kills, deaths: m.deaths, assists: m.assists,
      kd: m.deaths ? m.kills / m.deaths : m.kills, kda: m.kda, acs: m.score,
      adr: null, hs_rate: null, played_at: m.played_at,
    }));
  }, [source, comp, history]);

  // フィルタ選択肢
  const mapOptions = useMemo(() => Array.from(new Set(rawRows.map((r) => r.map_name).filter(Boolean))) as string[], [rawRows]);
  const agentOptions = useMemo(() => Array.from(new Set(rawRows.map((r) => r.agent).filter(Boolean))) as string[], [rawRows]);

  const rows = rawRows.filter((r) => {
    if (mapFilter && r.map_name !== mapFilter) return false;
    if (agentFilter && r.agent !== agentFilter) return false;
    if (resultFilter === "win" && r.won !== true) return false;
    if (resultFilter === "loss" && r.won !== false) return false;
    return true;
  });

  return (
    <div className="space-y-5 pt-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-brand-500/10 p-1.5"><Swords className="h-4 w-4 text-brand-400" /></div>
          <h2 className="text-sm font-bold text-white">Matches</h2>
        </div>
        <SourceToggle value={source} onChange={setSource} />
      </div>

      {/* フィルタ */}
      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-white/10 bg-slate-900 p-3">
        <span className="flex items-center gap-1.5 text-xs text-slate-500"><Search className="h-3.5 w-3.5" />絞り込み</span>
        <select value={mapFilter} onChange={(e) => setMapFilter(e.target.value)} className={sel}>
          <option value="">全Map</option>
          {mapOptions.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        <select value={agentFilter} onChange={(e) => setAgentFilter(e.target.value)} className={sel}>
          <option value="">全Agent</option>
          {agentOptions.map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
        <select value={resultFilter} onChange={(e) => setResultFilter(e.target.value as ResultFilter)} className={sel}>
          <option value="all">勝敗すべて</option>
          <option value="win">勝利のみ</option>
          <option value="loss">敗北のみ</option>
        </select>
        {(mapFilter || agentFilter || resultFilter !== "all") && (
          <button onClick={() => { setMapFilter(""); setAgentFilter(""); setResultFilter("all"); }}
            className="ml-auto text-xs text-slate-500 hover:text-white transition-colors">クリア</button>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-2">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-12 animate-pulse rounded-lg bg-white/5" />)}</div>
      ) : rows.length === 0 ? (
        <EmptyState icon={Swords} title="試合データがありません"
          desc={source === "competitive" ? "Riot連携・同期後に表示されます。" : "大会参加後に表示されます。"} />
      ) : (
        <MatchTable rows={rows} />
      )}
    </div>
  );
}
