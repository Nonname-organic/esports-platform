"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Save, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MatchGame, MatchTeam } from "@/types/match";

const scoreSchema = z.object({
  team1_score: z.coerce.number().int("整数を入力").min(0, "0以上").max(999),
  team2_score: z.coerce.number().int("整数を入力").min(0, "0以上").max(999),
  map_id: z.string().optional(),
  map_name: z.string().optional(),
  duration_minutes: z.coerce.number().int().min(0).max(180).optional().or(z.literal("")),
});

type ScoreFormValues = z.infer<typeof scoreSchema>;

// ゲーム別マッププール
const GAME_MAPS: Record<string, { id: string; name: string }[]> = {
  VALORANT: [
    { id: "ascent", name: "Ascent" }, { id: "bind", name: "Bind" },
    { id: "haven", name: "Haven" }, { id: "icebox", name: "Icebox" },
    { id: "pearl", name: "Pearl" }, { id: "lotus", name: "Lotus" },
    { id: "fracture", name: "Fracture" }, { id: "breeze", name: "Breeze" },
    { id: "sunset", name: "Sunset" }, { id: "abyss", name: "Abyss" },
  ],
  CS2: [
    { id: "mirage", name: "Mirage" }, { id: "inferno", name: "Inferno" },
    { id: "dust2", name: "Dust2" }, { id: "overpass", name: "Overpass" },
    { id: "ancient", name: "Ancient" }, { id: "nuke", name: "Nuke" },
    { id: "vertigo", name: "Vertigo" }, { id: "anubis", name: "Anubis" },
  ],
  LOL: [{ id: "summoners_rift", name: "サモナーズリフト" }],
  APEX: [
    { id: "worlds_edge", name: "ワールズエッジ" },
    { id: "broken_moon", name: "ブロークンムーン" },
    { id: "storm_point", name: "ストームポイント" },
    { id: "kings_canyon", name: "キングスキャニオン" },
    { id: "olympus", name: "オリンパス" },
  ],
  OVERWATCH: [
    { id: "kings_row", name: "キングスロウ" }, { id: "dorado", name: "ドラド" },
    { id: "numbani", name: "ヌンバニ" }, { id: "circuit_royal", name: "サーキットロイヤル" },
    { id: "midtown", name: "ミッドタウン" }, { id: "rialto", name: "リアルト" },
  ],
};

interface ScoreFormProps {
  gameNumber: number;
  team1: MatchTeam | null;
  team2: MatchTeam | null;
  currentGame: MatchGame | undefined;
  game: string;
  isDisabled: boolean;
  onSubmit: (data: {
    gameNumber: number;
    team1_score: number;
    team2_score: number;
    duration_seconds?: number;
  }) => Promise<void>;
}

export function ScoreForm({
  gameNumber,
  team1,
  team2,
  currentGame,
  game,
  isDisabled,
  onSubmit,
}: ScoreFormProps) {
  const maps = GAME_MAPS[game] ?? [];

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ScoreFormValues>({
    resolver: zodResolver(scoreSchema),
    defaultValues: {
      team1_score: currentGame?.team1_score ?? 0,
      team2_score: currentGame?.team2_score ?? 0,
      map_id: currentGame?.map_id ?? "",
      duration_minutes: "",
    },
  });

  const submit = handleSubmit(async (values) => {
    await onSubmit({
      gameNumber,
      team1_score: values.team1_score,
      team2_score: values.team2_score,
      duration_seconds:
        values.duration_minutes !== "" && values.duration_minutes != null
          ? Number(values.duration_minutes) * 60
          : undefined,
    });
    reset({ ...values });
  });

  return (
    <form onSubmit={submit} className="space-y-5">
      {/* マップ選択 */}
      <div>
        <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-500">
          マップ
        </label>
        <select
          {...register("map_id")}
          disabled={isDisabled}
          className="w-full rounded-lg border border-white/10 bg-slate-800 px-3 py-2.5 text-sm text-white outline-none focus:border-brand-500 disabled:opacity-50"
        >
          <option value="">マップを選択...</option>
          {maps.map((m) => (
            <option key={m.id} value={m.id}>{m.name}</option>
          ))}
        </select>
        {currentGame?.map_name && (
          <p className="mt-1 text-xs text-slate-500">現在: {currentGame.map_name}</p>
        )}
      </div>

      {/* スコア入力 */}
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4">
        {/* Team1 */}
        <div>
          <label className="mb-1.5 block truncate text-xs font-semibold text-slate-400">
            {team1?.name ?? "Team A"}
          </label>
          <input
            type="number"
            {...register("team1_score")}
            min={0}
            disabled={isDisabled}
            className={cn(
              "w-full rounded-lg border bg-slate-800 px-3 py-3 text-center text-2xl font-black text-white outline-none transition-colors",
              errors.team1_score
                ? "border-red-500"
                : "border-white/10 focus:border-brand-500",
              isDisabled && "opacity-50",
            )}
          />
          {errors.team1_score && (
            <p className="mt-1 text-xs text-red-400">{errors.team1_score.message}</p>
          )}
        </div>

        <span className="mt-5 text-xl font-black text-slate-600">–</span>

        {/* Team2 */}
        <div>
          <label className="mb-1.5 block truncate text-right text-xs font-semibold text-slate-400">
            {team2?.name ?? "Team B"}
          </label>
          <input
            type="number"
            {...register("team2_score")}
            min={0}
            disabled={isDisabled}
            className={cn(
              "w-full rounded-lg border bg-slate-800 px-3 py-3 text-center text-2xl font-black text-white outline-none transition-colors",
              errors.team2_score
                ? "border-red-500"
                : "border-white/10 focus:border-brand-500",
              isDisabled && "opacity-50",
            )}
          />
          {errors.team2_score && (
            <p className="mt-1 text-xs text-red-400">{errors.team2_score.message}</p>
          )}
        </div>
      </div>

      {/* 試合時間 */}
      <div>
        <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-500">
          試合時間（分）
        </label>
        <input
          type="number"
          {...register("duration_minutes")}
          min={0}
          max={180}
          placeholder="例: 45"
          disabled={isDisabled}
          className="w-full rounded-lg border border-white/10 bg-slate-800 px-3 py-2.5 text-sm text-white outline-none focus:border-brand-500 disabled:opacity-50"
        />
      </div>

      {/* 送信ボタン */}
      <button
        type="submit"
        disabled={isDisabled || isSubmitting}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-500 py-3 text-sm font-bold text-white hover:bg-brand-600 transition-colors disabled:opacity-40"
      >
        <Save className="h-4 w-4" />
        {isSubmitting ? "更新中..." : `Game ${gameNumber} スコア更新`}
      </button>
    </form>
  );
}

export { GAME_MAPS };
