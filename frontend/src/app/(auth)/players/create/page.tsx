"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useRequireAuth } from "@/hooks/use-require-auth";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { User2, AlertCircle, Gamepad2, Info, Trash2, ExternalLink, Loader2, UserSearch } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { cn, getGameColor } from "@/lib/utils";
import type { GameType } from "@/types/tournament";

const GAMES: { value: GameType; label: string; color: string }[] = [
  { value: "VALORANT", label: "VALORANT", color: "border-red-500/50 text-red-400 bg-red-500/5" },
  { value: "LOL", label: "League of Legends", color: "border-yellow-500/50 text-yellow-400 bg-yellow-500/5" },
  { value: "APEX", label: "Apex Legends", color: "border-cyan-500/50 text-cyan-400 bg-cyan-500/5" },
  { value: "CS2", label: "CS2", color: "border-orange-500/50 text-orange-400 bg-orange-500/5" },
  { value: "OVERWATCH", label: "Overwatch 2", color: "border-blue-500/50 text-blue-400 bg-blue-500/5" },
];

const schema = z.object({
  game: z.enum(["VALORANT", "LOL", "APEX", "CS2", "OVERWATCH"] as const),
  riot_id: z.string().min(1, "Riot IDを入力してください").max(111),
  discord_id: z.string().max(100).optional(),
});

type FormValues = z.infer<typeof schema>;

export default function PlayerPage() {
  const { ready, authed } = useRequireAuth();
  const router = useRouter();
  const qc = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data: myPlayer, isLoading: meLoading } = useQuery({
    queryKey: ["players", "me"],
    queryFn: () => apiClient.get<{ data: any | null }>("/api/v1/players/me"),
    select: (res) => res.data,
  });

  const create = useMutation({
    mutationFn: (values: FormValues) =>
      apiClient.post("/api/v1/players", {
        game: values.game,
        riot_id: values.riot_id,
        discord_id: values.discord_id || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["players", "me"] });
    },
  });

  const unregister = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/api/v1/players/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["players", "me"] });
      setConfirmDelete(false);
    },
  });

  const {
    register, handleSubmit, watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { game: "VALORANT" },
  });

  const selectedGame = watch("game");

  const inputCls = (err?: boolean) => cn(
    "w-full rounded-xl border bg-white/5 px-4 py-3 text-sm text-white placeholder-slate-600 outline-none transition-colors",
    err ? "border-red-500/50 focus:border-red-500" : "border-white/10 focus:border-brand-500",
  );

  if (!ready || !authed) return null;

  if (meLoading) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  // 登録済みの場合：プレイヤー情報を表示
  if (myPlayer) {
    return (
      <div className="mx-auto max-w-lg px-4 py-10">
        <div className="mb-6 flex items-center gap-3">
          <div className="rounded-2xl bg-brand-500/10 p-3">
            <User2 className="h-7 w-7 text-brand-400" />
          </div>
          <div>
            <h1 className="text-2xl font-black text-white">プレイヤー</h1>
            <p className="text-sm text-slate-500">登録済みのプレイヤー情報</p>
          </div>
        </div>

        {/* プレイヤーカード */}
        <div className="rounded-2xl border border-white/10 bg-slate-900 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <span className={cn("rounded-full border px-3 py-1 text-xs font-bold", getGameColor(myPlayer.game))}>
              {myPlayer.game}
            </span>
            <a
              href={`/players/${myPlayer.id}`}
              className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
            >
              公開プロフィール <ExternalLink className="h-3 w-3" />
            </a>
          </div>

          <div className="space-y-3">
            <div>
              <p className="text-xs text-slate-500 mb-1">Riot ID</p>
              <p className="text-sm font-semibold text-white">{myPlayer.riot_id}</p>
            </div>
            {myPlayer.discord_id && (
              <div>
                <p className="text-xs text-slate-500 mb-1">Discord</p>
                <p className="text-sm text-white">{myPlayer.discord_id}</p>
              </div>
            )}
            <div>
              <p className="text-xs text-slate-500 mb-1">登録日</p>
              <p className="text-sm text-white">
                {new Date(myPlayer.created_at).toLocaleDateString("ja-JP")}
              </p>
            </div>
          </div>
        </div>

        {/* チームを探す (LFT) */}
        <a
          href="/scout/lft/me"
          className="mt-4 flex items-center justify-between rounded-2xl border border-purple-500/20 bg-purple-500/5 p-5 hover:bg-purple-500/10 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-purple-500/10 p-2.5">
              <UserSearch className="h-5 w-5 text-purple-400" />
            </div>
            <div>
              <p className="text-sm font-bold text-white">チームを探す (LFT)</p>
              <p className="text-xs text-slate-500">プロフィールを使ってチーム募集をアピール</p>
            </div>
          </div>
          <ExternalLink className="h-4 w-4 text-slate-500" />
        </a>

        {/* 登録解除 */}
        <div className="mt-6 rounded-2xl border border-red-500/20 bg-red-500/5 p-5">
          <h2 className="mb-2 flex items-center gap-2 text-sm font-bold text-red-400">
            <Trash2 className="h-4 w-4" /> プレイヤー登録を解除
          </h2>
          <p className="mb-4 text-xs text-slate-500">
            解除するとチームメンバーシップも失われます。再登録は可能です。
          </p>
          {!confirmDelete ? (
            <button
              onClick={() => setConfirmDelete(true)}
              className="rounded-lg border border-red-500/30 px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
            >
              登録解除へ
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <button
                onClick={() => unregister.mutate(myPlayer.id)}
                disabled={unregister.isPending}
                className="flex items-center gap-2 rounded-lg bg-red-500 px-4 py-2 text-sm font-bold text-white hover:bg-red-600 disabled:opacity-40 transition-colors"
              >
                {unregister.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                解除する
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
              >
                キャンセル
              </button>
            </div>
          )}
          {unregister.isError && (
            <p className="mt-2 text-xs text-red-400">
              {unregister.error instanceof Error ? unregister.error.message : "解除に失敗しました"}
            </p>
          )}
        </div>
      </div>
    );
  }

  // 未登録の場合：登録フォームを表示
  return (
    <div className="mx-auto max-w-lg px-4 py-10">
      <div className="mb-8 flex items-center gap-3">
        <div className="rounded-2xl bg-brand-500/10 p-3">
          <User2 className="h-7 w-7 text-brand-400" />
        </div>
        <div>
          <h1 className="text-2xl font-black text-white">プレイヤー登録</h1>
          <p className="text-sm text-slate-500">チームに参加してトーナメントに出場しよう</p>
        </div>
      </div>

      <form onSubmit={handleSubmit((v) => create.mutate(v))} className="space-y-5">
        {create.isError && (
          <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            {create.error instanceof Error ? create.error.message : "登録に失敗しました"}
          </div>
        )}

        {/* ゲーム選択 */}
        <div className="rounded-2xl border border-white/10 bg-slate-900 p-5 space-y-3">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Gamepad2 className="h-4 w-4 text-brand-400" />
            プレイするゲーム
          </h2>
          <div className="space-y-2">
            {GAMES.map((g) => (
              <label key={g.value} className={cn(
                "flex cursor-pointer items-center gap-3 rounded-xl border p-3.5 transition-colors",
                selectedGame === g.value ? g.color : "border-white/8 text-slate-400 hover:border-white/15",
              )}>
                <input type="radio" {...register("game")} value={g.value} className="sr-only" />
                <div className={cn("h-2.5 w-2.5 rounded-full border-2",
                  selectedGame === g.value ? "border-current bg-current" : "border-slate-600")} />
                <span className="text-sm font-semibold">{g.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Riot ID */}
        <div className="rounded-2xl border border-white/10 bg-slate-900 p-5 space-y-4">
          <h2 className="text-sm font-bold text-white">ゲーム情報</h2>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-400">
              Riot ID <span className="text-red-400">*</span>
            </label>
            <input
              {...register("riot_id")}
              className={inputCls(!!errors.riot_id)}
              placeholder="例: PlayerName#JP1"
            />
            {errors.riot_id && <p className="mt-1 text-xs text-red-400">{errors.riot_id.message}</p>}
            <p className="mt-1.5 flex items-center gap-1 text-xs text-slate-600">
              <Info className="h-3 w-3" />
              Name#TAGの形式で入力（例: SEN Tenz#NA1）
            </p>
          </div>
        </div>

        {/* Discord */}
        <div className="rounded-2xl border border-white/10 bg-slate-900 p-5">
          <h2 className="mb-3 text-sm font-bold text-white">Discord（任意）</h2>
          <input
            {...register("discord_id")}
            className={inputCls()}
            placeholder="username または username#1234"
          />
          <p className="mt-1.5 text-xs text-slate-600">チームマネージャーからの連絡に使用されます</p>
        </div>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={isSubmitting || create.isPending}
            className="flex-1 rounded-xl bg-brand-500 py-3 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-40 transition-colors"
          >
            {isSubmitting || create.isPending ? "登録中..." : "プレイヤー登録する"}
          </button>
          <button type="button" onClick={() => router.back()}
            className="rounded-xl border border-white/10 px-5 py-3 text-sm text-slate-400 hover:text-white transition-colors">
            キャンセル
          </button>
        </div>
      </form>
    </div>
  );
}
