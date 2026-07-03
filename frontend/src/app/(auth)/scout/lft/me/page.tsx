"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Trash2, Loader2, ExternalLink } from "lucide-react";
import { useRequireAuth } from "@/hooks/use-require-auth";
import { useMyLFT, useCreateLFT, useUpdateMyLFT, useDeleteMyLFT } from "@/features/lft/hooks/use-lft";
import { apiClient } from "@/lib/api-client";
import { LFTForm, RANKS, REGIONS } from "../_components/lft-form";
import type { LFTPost } from "@/features/lft/api/lft-api";

interface MyPlayer {
  id: string;
  in_game_name: string;
  rank: string | null;
  main_role: string | null;
  sub_roles: string[] | null;
  agent_pool: string[] | null;
  region: string | null;
  discord_id: string | null;
  twitter_handle: string | null;
}

/** プロフィール値が選択肢に含まれる場合のみ初期値に使う（不一致なら空で編集を促す） */
function safeInList(value: string | null | undefined, list: string[]): string {
  return value && list.includes(value) ? value : "";
}

export default function MyLFTPage() {
  const { ready, authed } = useRequireAuth();
  const router = useRouter();
  const { data: lft, isLoading: lftLoading } = useMyLFT();
  const { data: player, isLoading: playerLoading } = useQuery({
    queryKey: ["players", "me"],
    queryFn: () => apiClient.get<{ data: MyPlayer | null }>("/api/v1/players/me"),
    select: (res) => res.data,
  });
  const create = useCreateLFT();
  const update = useUpdateMyLFT();
  const deleteLFT = useDeleteMyLFT();
  const [confirmDelete, setConfirmDelete] = useState(false);

  if (!ready || !authed) return null;

  if (lftLoading || playerLoading) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  // プレイヤー未登録
  if (!player) {
    return (
      <div className="mx-auto max-w-lg px-4 py-20 text-center">
        <p className="text-slate-400">LFTを登録するにはプレイヤー登録が必要です。</p>
        <Link href="/players/create" className="mt-4 inline-block rounded-xl bg-brand-500 px-5 py-2 text-sm font-bold text-white hover:bg-brand-600 transition-colors">
          プレイヤー登録へ
        </Link>
      </div>
    );
  }

  // プロフィールからの初期値（既存LFTがあればそちらを優先）
  const roles: string[] = lft?.roles?.length
    ? lft.roles
    : [player.main_role, ...(player.sub_roles ?? [])].filter(Boolean) as string[];

  const defaultValues: Partial<LFTPost> & { player_name?: string } = {
    ...(lft ?? {}),
    player_name: player.in_game_name,
    roles,
    current_rank: lft?.current_rank ?? safeInList(player.rank, RANKS),
    peak_rank: lft?.peak_rank ?? "",
    region: lft?.region ?? safeInList(player.region, REGIONS),
    agents: lft?.agents ?? (player.agent_pool ?? []),
    discord: lft?.discord ?? (player.discord_id ?? ""),
    twitter: lft?.twitter ?? (player.twitter_handle ?? ""),
  };

  const handleDelete = async () => {
    await deleteLFT.mutateAsync();
    setConfirmDelete(false);
  };

  return (
    <div>
      {lft && (
        <div className="mx-auto max-w-2xl px-4 pt-6">
          <div className="flex items-center justify-between rounded-xl border border-white/10 bg-slate-900 px-4 py-3">
            <p className="text-sm text-slate-400">現在LFTを公開中です</p>
            <div className="flex items-center gap-2">
              <Link href={`/scout/lft/${lft.id}`}
                className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:text-white transition-colors">
                <ExternalLink className="h-3.5 w-3.5" /> 公開ページ
              </Link>
              {!confirmDelete ? (
                <button onClick={() => setConfirmDelete(true)}
                  className="flex items-center gap-1.5 rounded-lg bg-red-500/10 px-3 py-1.5 text-xs text-red-400 hover:bg-red-500/20 transition-colors">
                  <Trash2 className="h-3.5 w-3.5" /> 削除
                </button>
              ) : (
                <div className="flex items-center gap-1.5">
                  <button onClick={handleDelete} disabled={deleteLFT.isPending}
                    className="flex items-center gap-1 rounded-lg bg-red-500 px-3 py-1.5 text-xs font-bold text-white hover:bg-red-600 disabled:opacity-50 transition-colors">
                    {deleteLFT.isPending && <Loader2 className="h-3 w-3 animate-spin" />} 削除する
                  </button>
                  <button onClick={() => setConfirmDelete(false)}
                    className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:text-white transition-colors">
                    取消
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <LFTForm
        defaultValues={defaultValues}
        isEdit={!!lft}
        isSubmitting={create.isPending || update.isPending}
        error={
          create.isError ? (create.error instanceof Error ? create.error.message : "登録に失敗しました")
          : update.isError ? (update.error instanceof Error ? update.error.message : "更新に失敗しました")
          : undefined
        }
        onSubmit={async (data) => {
          if (lft) {
            await update.mutateAsync(data);
          } else {
            await create.mutateAsync(data);
          }
          router.push("/scout/lft");
        }}
      />
    </div>
  );
}
