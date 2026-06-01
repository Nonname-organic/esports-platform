"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { User2, AlertCircle, Info, CheckCircle2, Gamepad2 } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { GameType } from "@/types/tournament";

const GAMES: { value: GameType; label: string; color: string }[] = [
  { value: "VALORANT", label: "VALORANT", color: "border-red-500/50 text-red-400 bg-red-500/5" },
  { value: "LOL", label: "League of Legends", color: "border-yellow-500/50 text-yellow-400 bg-yellow-500/5" },
  { value: "APEX", label: "Apex Legends", color: "border-cyan-500/50 text-cyan-400 bg-cyan-500/5" },
  { value: "CS2", label: "CS2", color: "border-orange-500/50 text-orange-400 bg-orange-500/5" },
  { value: "OVERWATCH", label: "Overwatch 2", color: "border-blue-500/50 text-blue-400 bg-blue-500/5" },
];

const RANK_OPTIONS: Record<GameType, string[]> = {
  VALORANT: ["アイアン", "ブロンズ", "シルバー", "ゴールド", "プラチナ", "ダイヤモンド", "アセンダント", "イモータル", "ラディアント"],
  LOL: ["アイアン", "ブロンズ", "シルバー", "ゴールド", "プラチナ", "エメラルド", "ダイヤモンド", "マスター", "グランドマスター", "チャレンジャー"],
  APEX: ["ブロンズ", "シルバー", "ゴールド", "プラチナ", "ダイヤモンド", "マスター", "プレデター"],
  CS2: ["シルバー", "ゴールドノバ", "MG", "MG2", "MGE", "DMG", "LEM", "SMFC", "GE"],
  OVERWATCH: ["ブロンズ", "シルバー", "ゴールド", "プラチナ", "ダイヤモンド", "マスター", "グランドマスター", "チャンピオン"],
};

const schema = z.object({
  game: z.enum(["VALORANT", "LOL", "APEX", "CS2", "OVERWATCH"] as const),
  riot_id: z.string().min(1, "Riot IDを入力してください").max(111),
  peak_rank: z.string().optional(),
  current_rank: z.string().optional(),
  discord_id: z.string().max(100).optional(),
});

type FormValues = z.infer<typeof schema>;

export default function PlayerCreatePage() {
  const router = useRouter();
  const qc = useQueryClient();

  const { data: myPlayer } = useQuery({
    queryKey: ["players", "me"],
    queryFn: () => apiClient.get<{ data: any | null }>("/api/v1/players/me"),
    select: (res) => res.data,
  });

  const create = useMutation({
    mutationFn: (values: FormValues) =>
      apiClient.post("/api/v1/players", {
        game: values.game,
        riot_id: values.riot_id,
        rank: values.current_rank,
        discord_id: values.discord_id || undefined,
        bio: values.peak_rank ? `最高ランク: ${values.peak_rank}` : undefined,
      }),
    onSuccess: (res: any) => {
      qc.invalidateQueries({ queryKey: ["players"] });
      router.push(`/players/${res.data.id}`);
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
  const ranks = RANK_OPTIONS[selectedGame] ?? [];

  const inputCls = (err?: boolean) => cn(
    "w-full rounded-xl border bg-white/5 px-4 py-3 text-sm text-white placeholder-slate-600 outline-none transition-colors",
    err ? "border-red-500/50 focus:border-red-500" : "border-white/10 focus:border-brand-500",
  );

  if (myPlayer) {
    return (
      <div className="mx-auto max-w-lg px-4 py-20 text-center">
        <div className="mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-2xl bg-green-500/10">
          <CheckCircle2 className="h-10 w-10 text-green-400" />
        </div>
        <h1 className="text-xl font-black text-white">登録済みです</h1>
        <p className="mt-2 text-sm text-slate-400">既にプレイヤープロフィールが作成されています。</p>
        <button onClick={() => router.push(`/players/${myPlayer.id}`)}
          className="mt-6 rounded-xl bg-brand-500 px-6 py-2.5 text-sm font-bold text-white hover:bg-brand-600 transition-colors">
          プロフィールを見る
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg px-4 py-10">
      {/* ヘッダー */}
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

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-400">現在ランク</label>
              <select {...register("current_rank")} className={cn(inputCls(), "bg-slate-800")}>
                <option value="">選択してください</option>
                {ranks.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-400">最高ランク</label>
              <select {...register("peak_rank")} className={cn(inputCls(), "bg-slate-800")}>
                <option value="">選択してください</option>
                {ranks.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
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
