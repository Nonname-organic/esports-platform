"use client";

import { useState } from "react";
import { Link2, RefreshCw, AlertCircle, CheckCircle2, Gamepad2 } from "lucide-react";
import { useRiotProfile, useLinkRiot, useSyncRiot } from "@/features/riot/hooks/use-riot";
import { useAuthStore } from "@/store/auth-store";
import { cn } from "@/lib/utils";

interface RiotTabProps {
  playerId: string;
  playerUserId?: string;
}

export function RiotTab({ playerId, playerUserId }: RiotTabProps) {
  const user = useAuthStore((s) => s.user);
  const { data: profile, isLoading } = useRiotProfile(playerId);
  const linkRiot = useLinkRiot();
  const syncRiot = useSyncRiot();
  const [riotIdInput, setRiotIdInput] = useState("");

  // 本人のみ編集可能
  const canEdit = user && (user.id === playerUserId || user.role === "admin");

  if (isLoading) {
    return <div className="h-48 animate-pulse rounded-xl bg-white/5 mt-6" />;
  }

  const handleLink = async () => {
    if (!riotIdInput.includes("#")) return;
    await linkRiot.mutateAsync({ playerId, riotId: riotIdInput });
    setRiotIdInput("");
  };

  return (
    <div className="space-y-5 pt-6">
      {/* 連携状態 */}
      <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <div className="mb-4 flex items-center gap-2">
          <div className="rounded-lg bg-red-500/10 p-2">
            <Gamepad2 className="h-5 w-5 text-red-400" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Riot Games 連携</h3>
            <p className="text-xs text-slate-500">VALORANT の戦績を自動取得</p>
          </div>
        </div>

        {profile ? (
          <div className="space-y-3">
            <div className="flex items-center gap-3 rounded-lg bg-white/3 px-4 py-3">
              <CheckCircle2 className="h-5 w-5 text-green-400" />
              <div className="flex-1">
                <p className="font-semibold text-white">{profile.riot_id}</p>
                <p className="text-xs text-slate-500">
                  {profile.synced_at ? `最終同期: ${new Date(profile.synced_at).toLocaleString("ja-JP")}` : "未同期"}
                </p>
              </div>
              {canEdit && (
                <button
                  onClick={() => syncRiot.mutate(playerId)}
                  disabled={syncRiot.isPending}
                  className="flex items-center gap-1.5 rounded-lg bg-brand-500/10 px-3 py-2 text-xs font-semibold text-brand-400 hover:bg-brand-500/20 disabled:opacity-50 transition-colors"
                >
                  <RefreshCw className={cn("h-3.5 w-3.5", syncRiot.isPending && "animate-spin")} />
                  同期
                </button>
              )}
            </div>
            {syncRiot.isError && (
              <p className="flex items-center gap-1 text-xs text-red-400">
                <AlertCircle className="h-3.5 w-3.5" />
                {syncRiot.error instanceof Error ? syncRiot.error.message : "同期に失敗しました"}
              </p>
            )}
            {syncRiot.isSuccess && (
              <p className="text-xs text-green-400">{syncRiot.data.data.synced_matches}件の試合を取得しました</p>
            )}
          </div>
        ) : canEdit ? (
          <div className="space-y-2">
            <p className="text-sm text-slate-400">Riot IDを連携して戦績を自動取得しましょう</p>
            <div className="flex gap-2">
              <input
                value={riotIdInput}
                onChange={(e) => setRiotIdInput(e.target.value)}
                placeholder="Name#TAG（例: PlayerName#JP1）"
                className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder-slate-600 outline-none focus:border-brand-500"
              />
              <button
                onClick={handleLink}
                disabled={linkRiot.isPending || !riotIdInput.includes("#")}
                className="flex items-center gap-1.5 rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-40 transition-colors"
              >
                <Link2 className="h-4 w-4" />連携
              </button>
            </div>
            {linkRiot.isError && (
              <p className="text-xs text-red-400">
                {linkRiot.error instanceof Error ? linkRiot.error.message : "連携に失敗しました"}
              </p>
            )}
          </div>
        ) : (
          <p className="text-sm text-slate-500">Riot連携されていません</p>
        )}
      </section>

      {/* 取得済み試合 */}
      {profile && profile.matches.length > 0 && (
        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h3 className="mb-4 text-sm font-bold text-white">Riot取得試合（最新{profile.matches.length}件）</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-white/8 text-slate-500">
                  <th className="pb-2 text-left">エージェント</th>
                  <th className="pb-2 text-left">マップ</th>
                  <th className="pb-2 text-center">K/D/A</th>
                  <th className="pb-2 text-center">ACS</th>
                  <th className="pb-2 text-center">結果</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {profile.matches.map((m) => (
                  <tr key={m.match_id}>
                    <td className="py-2 font-medium text-white">{m.agent ?? "—"}</td>
                    <td className="py-2 text-slate-400">{m.map_name ?? "—"}</td>
                    <td className="py-2 text-center tabular-nums">
                      <span className="text-green-400">{m.kills}</span>/
                      <span className="text-red-400">{m.deaths}</span>/
                      <span className="text-blue-400">{m.assists}</span>
                    </td>
                    <td className="py-2 text-center font-bold text-white">{m.acs ?? "—"}</td>
                    <td className="py-2 text-center">
                      {m.won === true ? <span className="text-green-400 font-bold">WIN</span> :
                       m.won === false ? <span className="text-red-400">LOSS</span> : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
