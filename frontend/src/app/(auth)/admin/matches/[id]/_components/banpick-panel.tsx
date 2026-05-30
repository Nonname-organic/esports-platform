"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Shield, XCircle, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MatchDetail, BanPick } from "@/types/match";
import type { useMatchAdmin } from "@/features/matches/hooks/use-match-admin";
import { GAME_MAPS } from "./score-form";

const bpSchema = z.object({
  team_id: z.string().min(1, "チームを選択"),
  action: z.enum(["ban", "pick"]),
  map_id: z.string().min(1, "マップを選択"),
});

type BPFormValues = z.infer<typeof bpSchema>;

interface BanPickPanelProps {
  match: MatchDetail;
  game: string;
  registerBanPick: ReturnType<typeof useMatchAdmin>["registerBanPick"];
}

// BO形式別 Ban/Pickシーケンス定義
const BP_SEQUENCE: Record<string, { action: "ban" | "pick"; team: 1 | 2 }[]> = {
  BO3: [
    { action: "ban", team: 1 }, { action: "ban", team: 2 },
    { action: "pick", team: 1 }, { action: "pick", team: 2 },
    { action: "ban", team: 1 }, { action: "ban", team: 2 },
    { action: "pick", team: 1 },  // tiebreaker
  ],
  BO5: [
    { action: "ban", team: 1 }, { action: "ban", team: 2 },
    { action: "pick", team: 1 }, { action: "pick", team: 2 },
    { action: "pick", team: 1 }, { action: "pick", team: 2 },
    { action: "ban", team: 1 }, { action: "ban", team: 2 },
    { action: "pick", team: 1 },  // tiebreaker
  ],
  BO1: [
    { action: "ban", team: 1 }, { action: "ban", team: 2 },
    { action: "ban", team: 1 }, { action: "ban", team: 2 },
    { action: "ban", team: 1 }, { action: "ban", team: 2 },
    { action: "pick", team: 1 }, // remaining
  ],
};

export function BanPickPanel({ match, game, registerBanPick }: BanPickPanelProps) {
  const [isAdding, setIsAdding] = useState(false);
  const maps = GAME_MAPS[game] ?? [];
  const sequence = BP_SEQUENCE[match.format] ?? [];
  const nextOrder = match.ban_picks.length + 1;
  const nextStep = sequence[nextOrder - 1];

  const isDisabled = match.status !== "ongoing";

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<BPFormValues>({
    resolver: zodResolver(bpSchema),
    defaultValues: {
      team_id: nextStep?.team === 1 ? (match.team1?.id ?? "") : (match.team2?.id ?? ""),
      action: nextStep?.action ?? "ban",
      map_id: "",
    },
  });

  const watchedAction = watch("action");

  const submit = handleSubmit(async (values) => {
    await registerBanPick.mutateAsync({
      ...values,
      order: nextOrder,
    });
    reset({
      team_id: "",
      action: "ban",
      map_id: "",
    });
    setIsAdding(false);
  });

  const usedMapIds = new Set(match.ban_picks.map((bp) => bp.map_id));

  return (
    <div className="rounded-xl border border-white/10 bg-slate-900">
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-3">
        <h2 className="text-sm font-bold text-white">Ban / Pick</h2>
        {!isDisabled && sequence.length > 0 && nextOrder <= sequence.length && (
          <button
            onClick={() => setIsAdding((v) => !v)}
            className={cn(
              "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors",
              isAdding
                ? "bg-white/5 text-slate-400"
                : "bg-brand-500/10 text-brand-400 hover:bg-brand-500/20",
            )}
          >
            <Plus className="h-3.5 w-3.5" />
            {isAdding ? "キャンセル" : "次のステップを登録"}
          </button>
        )}
      </div>

      {/* 登録済みBP一覧 */}
      <div className="divide-y divide-white/5">
        {match.ban_picks.length === 0 && !isAdding && (
          <p className="px-5 py-8 text-center text-sm text-slate-500">
            Ban/Pickはまだ登録されていません
          </p>
        )}

        {match.ban_picks
          .sort((a, b) => a.order - b.order)
          .map((bp) => (
            <BpRow
              key={bp.order}
              bp={bp}
              team1={match.team1}
              team2={match.team2}
              sequence={sequence}
            />
          ))}

        {/* 次のステップのプレビュー */}
        {!isAdding && nextOrder <= sequence.length && nextStep && (
          <div className="flex items-center gap-3 px-5 py-3 opacity-40">
            <OrderBadge order={nextOrder} />
            <ActionBadge action={nextStep.action} />
            <TeamLabel
              team={nextStep.team === 1 ? match.team1 : match.team2}
            />
            <span className="ml-auto text-xs text-slate-600">未登録</span>
          </div>
        )}
      </div>

      {/* 登録フォーム */}
      {isAdding && !isDisabled && (
        <form onSubmit={submit} className="border-t border-white/10 p-5 space-y-4">
          <p className="text-xs font-semibold text-slate-400">
            Step {nextOrder} を登録
            {nextStep && (
              <span className="ml-2 text-slate-600">
                （推奨: {nextStep.team === 1 ? match.team1?.name : match.team2?.name} が{" "}
                {nextStep.action === "ban" ? "BAN" : "PICK"}）
              </span>
            )}
          </p>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {/* チーム */}
            <div>
              <label className="mb-1 block text-xs text-slate-500">チーム</label>
              <select
                {...register("team_id")}
                className="w-full rounded-lg border border-white/10 bg-slate-800 px-3 py-2 text-sm text-white outline-none focus:border-brand-500"
              >
                <option value="">選択...</option>
                {match.team1 && <option value={match.team1.id}>{match.team1.name}</option>}
                {match.team2 && <option value={match.team2.id}>{match.team2.name}</option>}
              </select>
              {errors.team_id && (
                <p className="mt-1 text-xs text-red-400">{errors.team_id.message}</p>
              )}
            </div>

            {/* アクション */}
            <div>
              <label className="mb-1 block text-xs text-slate-500">アクション</label>
              <div className="flex gap-2">
                {(["ban", "pick"] as const).map((act) => (
                  <button
                    key={act}
                    type="button"
                    onClick={() => setValue("action", act)}
                    className={cn(
                      "flex-1 rounded-lg border py-2 text-xs font-bold uppercase transition-colors",
                      watchedAction === act
                        ? act === "ban"
                          ? "border-red-500/50 bg-red-500/10 text-red-400"
                          : "border-green-500/50 bg-green-500/10 text-green-400"
                        : "border-white/10 text-slate-500 hover:text-white",
                    )}
                  >
                    {act}
                  </button>
                ))}
              </div>
            </div>

            {/* マップ */}
            <div>
              <label className="mb-1 block text-xs text-slate-500">マップ</label>
              <select
                {...register("map_id")}
                className="w-full rounded-lg border border-white/10 bg-slate-800 px-3 py-2 text-sm text-white outline-none focus:border-brand-500"
              >
                <option value="">選択...</option>
                {maps.map((m) => (
                  <option key={m.id} value={m.id} disabled={usedMapIds.has(m.id)}>
                    {m.name} {usedMapIds.has(m.id) ? "(使用済)" : ""}
                  </option>
                ))}
              </select>
              {errors.map_id && (
                <p className="mt-1 text-xs text-red-400">{errors.map_id.message}</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-2 rounded-lg bg-brand-500 px-4 py-2 text-sm font-bold text-white hover:bg-brand-600 transition-colors disabled:opacity-40"
            >
              <CheckCircle2 className="h-4 w-4" />
              {isSubmitting ? "登録中..." : "登録"}
            </button>
          </div>

          {registerBanPick.isError && (
            <p className="text-xs text-red-400">
              <XCircle className="inline h-3.5 w-3.5 mr-1" />
              登録に失敗しました
            </p>
          )}
        </form>
      )}
    </div>
  );
}

function BpRow({
  bp,
  team1,
  team2,
  sequence,
}: {
  bp: BanPick;
  team1: MatchDetail["team1"];
  team2: MatchDetail["team2"];
  sequence: { action: "ban" | "pick"; team: 1 | 2 }[];
}) {
  const team = bp.team_id === team1?.id ? team1 : team2;

  return (
    <div className="flex items-center gap-3 px-5 py-3">
      <OrderBadge order={bp.order} />
      <ActionBadge action={bp.action} />
      <TeamLabel team={team} />
      <span className="flex-1 text-sm font-semibold text-white">{bp.map_name}</span>
      <span className="text-xs text-slate-600">{bp.map_id}</span>
    </div>
  );
}

function OrderBadge({ order }: { order: number }) {
  return (
    <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-white/5 text-xs font-bold text-slate-400">
      {order}
    </span>
  );
}

function ActionBadge({ action }: { action: "ban" | "pick" }) {
  return (
    <span
      className={cn(
        "flex-shrink-0 rounded px-1.5 py-0.5 text-[10px] font-black uppercase",
        action === "ban"
          ? "bg-red-500/10 text-red-400"
          : "bg-green-500/10 text-green-400",
      )}
    >
      {action}
    </span>
  );
}

function TeamLabel({ team }: { team: { name: string; logo_url: string | null } | null | undefined }) {
  return (
    <div className="flex flex-shrink-0 items-center gap-1.5">
      <div className="h-5 w-5 overflow-hidden rounded bg-slate-800 flex items-center justify-center">
        {team?.logo_url ? (
          <img src={team.logo_url} alt="" className="h-full w-full object-contain" />
        ) : (
          <Shield className="h-3 w-3 text-slate-600" />
        )}
      </div>
      <span className="text-xs text-slate-400">{team?.name ?? "TBD"}</span>
    </div>
  );
}
