"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Trophy, ChevronRight, AlertCircle, Check } from "lucide-react";
import { tournamentApi } from "@/features/tournaments/api/tournament-api";
import { cn } from "@/lib/utils";
import type { GameType } from "@/types/tournament";

// datetime-local（ローカル・空可）→ ISO(UTC)。空はundefined。
function toIsoDt(v?: string): string | undefined {
  if (!v) return undefined;
  const d = new Date(v);
  return isNaN(d.getTime()) ? undefined : d.toISOString();
}

const FIELD_LABELS: Record<string, string> = {
  name: "大会名",
  game: "ゲーム",
  format: "形式",
  max_teams: "最大チーム数",
  registration_start_at: "参加受付開始",
  registration_end_at: "参加受付終了",
  start_at: "大会開始",
  end_at: "大会終了",
};

const GAMES: GameType[] = ["VALORANT", "LOL", "APEX", "CS2", "OVERWATCH"];
const FORMATS = [
  { value: "single_elimination", label: "シングルエリミネーション", desc: "負けたら終わり。迅速な結果" },
  { value: "double_elimination", label: "ダブルエリミネーション", desc: "敗者復活あり。より公平な競争" },
  { value: "round_robin", label: "ラウンドロビン", desc: "全チームが対戦。リーグ形式" },
  { value: "swiss", label: "スイス式", desc: "成績に応じて対戦相手が決まる" },
];
const MAX_TEAMS_OPTIONS = [4, 8, 16, 32, 64, 128];
const BO_OPTIONS = ["BO1", "BO3", "BO5"];

const schema = z.object({
  name: z.string().min(2, "2文字以上").max(200, "200文字以内"),
  game: z.enum(["VALORANT", "LOL", "APEX", "CS2", "OVERWATCH"] as const),
  format: z.string().min(1),
  max_teams: z.number().int().min(2).max(256),
  description: z.string().max(2000).optional(),
  prize_pool: z.coerce.number().min(0).optional(),
  registration_start_at: z.string().min(1, "参加受付開始日時を入力してください"),
  registration_end_at: z.string().min(1, "参加受付終了日時を入力してください"),
  start_at: z.string().min(1, "大会開始日時を入力してください"),
  end_at: z.string().min(1, "大会終了日時を入力してください"),
  require_check_in: z.boolean().default(false),
  is_public: z.boolean().default(true),
  bo_format: z.string().default("BO3"),
});

type FormValues = z.infer<typeof schema>;

const STEPS = ["基本情報", "詳細設定", "日程設定", "確認"];

function StepIndicator({ step, current }: { step: number; current: number }) {
  const done = current > step;
  const active = current === step;
  return (
    <div className="flex items-center gap-2">
      <div className={cn(
        "flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-sm font-bold transition-colors",
        done ? "bg-green-500 text-white" : active ? "bg-brand-500 text-white" : "bg-white/5 text-slate-500",
      )}>
        {done ? <Check className="h-4 w-4" /> : step + 1}
      </div>
      <span className={cn("hidden text-sm font-medium sm:block", active ? "text-white" : "text-slate-500")}>
        {STEPS[step]}
      </span>
    </div>
  );
}

export default function TournamentNewPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [step, setStep] = useState(0);

  const {
    register, handleSubmit, watch, control,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { game: "VALORANT", format: "single_elimination", max_teams: 16, is_public: true, require_check_in: false, bo_format: "BO3" },
  });

  const create = useMutation({
    mutationFn: (values: FormValues) => tournamentApi.create({
      name: values.name,
      game: values.game,
      format: values.format,
      max_teams: values.max_teams,
      description: values.description,
      prize_pool: values.prize_pool,
      registration_start_at: toIsoDt(values.registration_start_at),
      registration_end_at: toIsoDt(values.registration_end_at),
      start_at: toIsoDt(values.start_at),
      end_at: toIsoDt(values.end_at),
      require_check_in: values.require_check_in,
      is_public: values.is_public,
      rules: { bo_format: values.bo_format },
    }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["tournaments", "mine"] });
      router.push(`/organizer/tournaments/${res.data.id}`);
    },
  });

  const values = watch();
  const inputCls = (err?: boolean) => cn(
    "w-full rounded-xl border bg-white/5 px-4 py-3 text-sm text-white placeholder-slate-600 outline-none transition-colors",
    err ? "border-red-500/50 focus:border-red-500" : "border-white/10 focus:border-brand-500",
  );

  const onSubmit = handleSubmit((data) => create.mutate(data));

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      {/* ヘッダー */}
      <div className="mb-8 flex items-center gap-3">
        <div className="rounded-2xl bg-brand-500/10 p-3">
          <Trophy className="h-7 w-7 text-brand-400" />
        </div>
        <div>
          <h1 className="text-2xl font-black text-white">大会を作成</h1>
          <p className="text-sm text-slate-500">4ステップで大会を公開できます</p>
        </div>
      </div>

      {/* ステップインジケーター */}
      <div className="mb-8 flex items-center gap-3">
        {STEPS.map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <StepIndicator step={i} current={step} />
            {i < STEPS.length - 1 && <ChevronRight className="h-4 w-4 text-slate-700" />}
          </div>
        ))}
      </div>

      <form onSubmit={onSubmit}>
        {/* Step 0: 基本情報 */}
        {step === 0 && (
          <div className="space-y-5 rounded-2xl border border-white/10 bg-slate-900 p-6">
            <h2 className="text-base font-bold text-white">基本情報</h2>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-400">大会名 <span className="text-red-400">*</span></label>
              <input {...register("name")} className={inputCls(!!errors.name)} placeholder="例: VALORANT Championship 2026 Spring" />
              {errors.name && <p className="mt-1 text-xs text-red-400">{errors.name.message}</p>}
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-400">ゲーム <span className="text-red-400">*</span></label>
              <div className="grid grid-cols-5 gap-2">
                {GAMES.map((g) => (
                  <label key={g} className={cn(
                    "cursor-pointer rounded-xl border py-3 text-center text-xs font-bold transition-colors",
                    values.game === g ? "border-brand-500 bg-brand-500/10 text-brand-400" : "border-white/10 text-slate-400 hover:text-white",
                  )}>
                    <input type="radio" {...register("game")} value={g} className="sr-only" />
                    {g}
                  </label>
                ))}
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-400">形式 <span className="text-red-400">*</span></label>
              <div className="space-y-2">
                {FORMATS.map((f) => (
                  <label key={f.value} className={cn(
                    "flex cursor-pointer items-start gap-3 rounded-xl border p-3.5 transition-colors",
                    values.format === f.value ? "border-brand-500 bg-brand-500/5" : "border-white/10 hover:border-white/20",
                  )}>
                    <input type="radio" {...register("format")} value={f.value} className="mt-0.5 accent-brand-500" />
                    <div>
                      <p className={cn("text-sm font-semibold", values.format === f.value ? "text-brand-400" : "text-white")}>{f.label}</p>
                      <p className="text-xs text-slate-500">{f.desc}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-400">最大チーム数</label>
                <Controller name="max_teams" control={control} render={({ field }) => (
                  <div className="flex flex-wrap gap-2">
                    {MAX_TEAMS_OPTIONS.map((n) => (
                      <button key={n} type="button" onClick={() => field.onChange(n)}
                        className={cn("rounded-lg border px-3 py-2 text-sm font-bold transition-colors",
                          field.value === n ? "border-brand-500 bg-brand-500/10 text-brand-400" : "border-white/10 text-slate-400 hover:text-white")}>
                        {n}
                      </button>
                    ))}
                  </div>
                )} />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-400">BO形式</label>
                <Controller name="bo_format" control={control} render={({ field }) => (
                  <div className="flex gap-2">
                    {BO_OPTIONS.map((bo) => (
                      <button key={bo} type="button" onClick={() => field.onChange(bo)}
                        className={cn("flex-1 rounded-lg border py-2 text-sm font-bold transition-colors",
                          field.value === bo ? "border-brand-500 bg-brand-500/10 text-brand-400" : "border-white/10 text-slate-400 hover:text-white")}>
                        {bo}
                      </button>
                    ))}
                  </div>
                )} />
              </div>
            </div>
          </div>
        )}

        {/* Step 1: 詳細設定 */}
        {step === 1 && (
          <div className="space-y-5 rounded-2xl border border-white/10 bg-slate-900 p-6">
            <h2 className="text-base font-bold text-white">詳細設定</h2>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-400">大会説明</label>
              <textarea {...register("description")} rows={5} className={inputCls()}
                placeholder="大会のルール、参加条件、賞品について記載してください..." />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-400">賞金総額（円）</label>
              <input type="number" {...register("prize_pool")} className={inputCls()} placeholder="例: 100000" min={0} />
            </div>
            <div className="space-y-3">
              <label className="flex cursor-pointer items-center gap-3">
                <input type="checkbox" {...register("is_public")} className="h-4 w-4 rounded accent-brand-500" />
                <div>
                  <p className="text-sm font-medium text-white">公開大会</p>
                  <p className="text-xs text-slate-500">チェックを外すと招待のみの非公開大会になります</p>
                </div>
              </label>
              <label className="flex cursor-pointer items-center gap-3">
                <input type="checkbox" {...register("require_check_in")} className="h-4 w-4 rounded accent-brand-500" />
                <div>
                  <p className="text-sm font-medium text-white">チェックイン必須</p>
                  <p className="text-xs text-slate-500">大会当日にチェックインを要求します</p>
                </div>
              </label>
            </div>
          </div>
        )}

        {/* Step 2: 日程設定 */}
        {step === 2 && (
          <div className="space-y-5 rounded-2xl border border-white/10 bg-slate-900 p-6">
            <h2 className="text-base font-bold text-white">日程設定</h2>
            {[
              { field: "registration_start_at" as const, label: "参加受付開始" },
              { field: "registration_end_at" as const, label: "参加受付終了" },
              { field: "start_at" as const, label: "大会開始" },
              { field: "end_at" as const, label: "大会終了" },
            ].map(({ field, label }) => (
              <div key={field}>
                <label className="mb-2 block text-sm font-medium text-slate-400">
                  {label} <span className="text-red-400">*</span>
                </label>
                <input type="datetime-local" {...register(field)} className={cn(inputCls(!!errors[field]), "[color-scheme:dark]")} />
                {errors[field] && <p className="mt-1 text-xs text-red-400">{errors[field]?.message}</p>}
              </div>
            ))}
            <p className="text-xs text-slate-600">※ 日程に応じてステータス（受付→開催中→終了）が自動更新されます。</p>
          </div>
        )}

        {/* Step 3: 確認 */}
        {step === 3 && (
          <div className="space-y-4 rounded-2xl border border-white/10 bg-slate-900 p-6">
            <h2 className="text-base font-bold text-white">確認</h2>
            {create.isError && (
              <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                {create.error instanceof Error ? create.error.message : "作成に失敗しました"}
              </div>
            )}
            <dl className="space-y-3 text-sm">
              {[
                { label: "大会名", value: values.name },
                { label: "ゲーム", value: values.game },
                { label: "形式", value: FORMATS.find((f) => f.value === values.format)?.label },
                { label: "最大チーム数", value: `${values.max_teams} チーム` },
                { label: "BO形式", value: values.bo_format },
                { label: "賞金", value: values.prize_pool ? `¥${Number(values.prize_pool).toLocaleString()}` : "なし" },
                { label: "公開設定", value: values.is_public ? "公開" : "非公開" },
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between border-b border-white/5 pb-2">
                  <dt className="text-slate-500">{label}</dt>
                  <dd className="font-semibold text-white">{value}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}

        {/* 入力エラー要約（どの項目が未入力か明示） */}
        {Object.keys(errors).length > 0 && (
          <div className="mt-6 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            <p className="flex items-center gap-2 font-semibold">
              <AlertCircle className="h-4 w-4" /> 入力に不備があります
            </p>
            <ul className="mt-1.5 list-disc pl-6 text-xs">
              {Object.entries(errors).map(([k, v]) => (
                <li key={k}>{FIELD_LABELS[k] ?? k}：{(v as { message?: string })?.message ?? "入力してください"}</li>
              ))}
            </ul>
          </div>
        )}

        {/* ナビゲーション */}
        <div className="mt-6 flex items-center justify-between">
          <button
            type="button"
            onClick={() => step > 0 ? setStep(step - 1) : router.back()}
            className="rounded-xl border border-white/10 px-5 py-2.5 text-sm text-slate-400 hover:text-white transition-colors"
          >
            {step === 0 ? "キャンセル" : "戻る"}
          </button>

          {step < STEPS.length - 1 ? (
            <button
              type="button"
              onClick={() => setStep(step + 1)}
              className="flex items-center gap-2 rounded-xl bg-brand-500 px-6 py-2.5 text-sm font-bold text-white hover:bg-brand-600 transition-colors"
            >
              次へ <ChevronRight className="h-4 w-4" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={create.isPending}
              className="flex items-center gap-2 rounded-xl bg-brand-500 px-6 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-40 transition-colors"
            >
              <Trophy className="h-4 w-4" />
              {create.isPending ? "作成中..." : "大会を作成する"}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
