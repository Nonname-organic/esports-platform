"use client";

import { useState } from "react";
import { Gamepad2, Link2, RefreshCw, AlertCircle, CheckCircle2, TrendingUp } from "lucide-react";
import { useCompetitive, useRiotProfile, useLinkRiot, useSyncRiot } from "@/features/riot/hooks/use-riot";
import { useAuthStore } from "@/store/auth-store";
import { cn } from "@/lib/utils";
import { StatsGrid } from "./shared/stats-grid";
import { MatchTable, type MatchRow } from "./shared/match-table";
import { RankChart } from "./shared/rank-chart";
import { SummaryCard } from "./shared/summary-card";
import { TabSkeleton, EmptyState } from "./shared/empty-state";
import { fmtNum, fmtInt, fmtPct, DASH } from "./shared/stat-format";

interface Props {
  playerId: string;
  playerUserId?: string;
}

export function PlayerCompetitive({ playerId, playerUserId }: Props) {
  const user = useAuthStore((s) => s.user);
  const { data: comp, isLoading } = useCompetitive(playerId);
  const { data: profile } = useRiotProfile(playerId);
  const linkRiot = useLinkRiot();
  const syncRiot = useSyncRiot();
  const [riotIdInput, setRiotIdInput] = useState("");

  const canEdit = user && (user.id === playerUserId || user.role === "admin");

  if (isLoading) return <TabSkeleton rows={2} />;

  const linked = comp?.linked ?? false;
  const cs = comp?.summary;
  const cr = comp?.rank;

  const handleLink = async () => {
    if (!riotIdInput.includes("#")) return;
    await linkRiot.mutateAsync({ playerId, riotId: riotIdInput });
    setRiotIdInput("");
  };

  const matchRows: MatchRow[] = (comp?.matches ?? []).map((m) => ({
    id: m.match_id,
    agent: m.agent,
    map_name: m.map_name,
    won: m.won,
    kills: m.kills, deaths: m.deaths, assists: m.assists,
    kd: m.kd, kda: m.kda, acs: m.acs, adr: m.adr, hs_rate: m.hs_rate,
    played_at: m.played_at,
  }));

  return (
    <div className="space-y-6 pt-6">
      {/* 連携ステータス */}
      <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <div className="mb-3 flex items-center gap-2">
          <div className="rounded-lg bg-red-500/10 p-2"><Gamepad2 className="h-5 w-5 text-red-400" /></div>
          <div>
            <h3 className="text-sm font-bold text-white">Riot Games 連携</h3>
            <p className="text-xs text-slate-500">VALORANT Competitive の戦績を分析</p>
          </div>
        </div>

        {linked ? (
          <div className="flex items-center gap-3 rounded-lg bg-white/3 px-4 py-3">
            <CheckCircle2 className="h-5 w-5 text-green-400" />
            <div className="flex-1">
              <p className="font-semibold text-white">{comp?.riot_id}</p>
              <p className="text-xs text-slate-500">
                {comp?.synced_at ? `最終同期: ${new Date(comp.synced_at).toLocaleString("ja-JP")}` : "未同期"}
              </p>
            </div>
            {canEdit && (
              <button onClick={() => syncRiot.mutate(playerId)} disabled={syncRiot.isPending}
                className="flex items-center gap-1.5 rounded-lg bg-brand-500/10 px-3 py-2 text-xs font-semibold text-brand-400 hover:bg-brand-500/20 disabled:opacity-50 transition-colors">
                <RefreshCw className={cn("h-3.5 w-3.5", syncRiot.isPending && "animate-spin")} /> 同期
              </button>
            )}
          </div>
        ) : canEdit ? (
          <div className="space-y-2">
            <p className="text-sm text-slate-400">Riot IDを連携して戦績を自動取得しましょう</p>
            <div className="flex gap-2">
              <input value={riotIdInput} onChange={(e) => setRiotIdInput(e.target.value)}
                placeholder="Name#TAG（例: PlayerName#JP1）"
                className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder-slate-600 outline-none focus:border-brand-500" />
              <button onClick={handleLink} disabled={linkRiot.isPending || !riotIdInput.includes("#")}
                className="flex items-center gap-1.5 rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-40 transition-colors">
                <Link2 className="h-4 w-4" /> 連携
              </button>
            </div>
            {linkRiot.isError && <p className="text-xs text-red-400">{linkRiot.error instanceof Error ? linkRiot.error.message : "連携に失敗しました"}</p>}
          </div>
        ) : (
          <p className="text-sm text-slate-500">Riot連携されていません</p>
        )}
        {syncRiot.isError && (
          <p className="mt-2 flex items-center gap-1 text-xs text-red-400">
            <AlertCircle className="h-3.5 w-3.5" />{syncRiot.error instanceof Error ? syncRiot.error.message : "同期に失敗しました"}
          </p>
        )}
      </section>

      {!linked ? (
        <EmptyState icon={Gamepad2} title="Competitiveデータがありません" desc="Riot IDを連携し同期すると、ランク・エージェント・マップ・試合データが表示されます。" />
      ) : (
        <>
          {/* ランク情報 */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <SummaryCard icon={Gamepad2} iconBg="bg-red-500/10" iconColor="text-red-400" label="Current Rank" main={cr?.current_rank ?? DASH} sub={cr?.current_rr != null ? `${cr.current_rr} RR` : "RR —"} />
            <SummaryCard icon={TrendingUp} iconBg="bg-yellow-500/10" iconColor="text-yellow-400" label="Peak Rank" main={cr?.peak_rank ?? DASH} sub={cr?.peak_rr != null ? `${cr.peak_rr} RR` : "RR —"} />
            <SummaryCard icon={CheckCircle2} iconBg="bg-green-500/10" iconColor="text-green-400" label="勝率" main={fmtPct(cs?.win_rate)} sub={`${fmtInt(cs?.wins)}W ${fmtInt(cs?.losses)}L`} />
            <SummaryCard icon={TrendingUp} iconBg="bg-brand-500/10" iconColor="text-brand-400" label="直近20試合" main={fmtPct(cs?.recent20_win_rate)} sub="勝率" />
          </div>

          {/* 総合スタッツ */}
          <StatsGrid
            title="総合スタッツ"
            cols={4}
            items={[
              { label: "ACS", value: fmtNum(cs?.acs, 0), highlight: true },
              { label: "ADR", value: fmtNum(cs?.adr, 0) },
              { label: "KD", value: fmtNum(cs?.kd, 2) },
              { label: "KDA", value: fmtNum(cs?.kda, 2) },
              { label: "HS%", value: cs?.hs_rate != null ? fmtPct(cs.hs_rate) : DASH },
              { label: "KAST", value: cs?.kast != null ? fmtPct(cs.kast) : DASH },
              { label: "FK率", value: cs?.fk_rate != null ? fmtPct(cs.fk_rate) : DASH },
              { label: "Clutch率", value: cs?.clutch_rate != null ? fmtPct(cs.clutch_rate) : DASH },
              { label: "Damage/Round", value: fmtNum(cs?.damage_per_round, 0) },
              { label: "First Blood", value: cs?.fk_rate != null ? fmtPct(cs.fk_rate) : DASH },
              { label: "First Death", value: cs?.fd_rate != null ? fmtPct(cs.fd_rate) : DASH },
              { label: "Assist", value: fmtNum(cs?.avg_assists, 1) },
            ]}
          />

          {/* ランク推移 */}
          <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
            <h3 className="mb-4 text-sm font-bold text-white">ランク推移（RR）</h3>
            <RankChart
              data={(comp?.rank_history ?? []).map((h) => ({ label: `${h.episode} ${h.act}`, value: h.rr, sub: h.rank }))}
            />
          </section>

          {/* 最近20試合 */}
          <section className="space-y-3">
            <h3 className="text-sm font-bold text-white">最近の試合（{matchRows.length}件）</h3>
            {matchRows.length > 0 ? <MatchTable rows={matchRows} /> : (
              <EmptyState title="試合データがありません" desc="同期後に最新の試合が表示されます。" />
            )}
          </section>
        </>
      )}
    </div>
  );
}
