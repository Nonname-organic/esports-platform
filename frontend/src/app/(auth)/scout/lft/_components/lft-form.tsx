"use client";

import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Link from "next/link";
import { ChevronRight, AlertCircle, Loader2, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { VALORANT_AGENTS, VALORANT_RANKS } from "@/lib/valorant";
import type { LFTCreateInput, LFTPost } from "@/features/lft/api/lft-api";

export const ROLES = ["Duelist", "Initiator", "Controller", "Sentinel", "Flex", "IGL"];
// ランクは division 付き25段階（lib/valorant.ts に集約）。既存 import 互換のため再エクスポート
export const RANKS = VALORANT_RANKS;
export const REGIONS = ["全国", "北海道", "東北", "関東", "中部", "関西", "中国", "四国", "九州", "海外", "オンラインのみ"];
export const ACTIVITY_TIMES = ["平日昼", "平日夜", "土日昼", "土日夜", "不定期"];

// エージェント一覧は lib/valorant.ts に集約している（既存の import 互換のため再エクスポート）
export { VALORANT_AGENTS };

const schema = z.object({
  status: z.enum(["open", "negotiating", "closed"]),
  roles: z.array(z.string()).min(1, "ロールを1つ以上選択してください"),
  current_rank: z.string().min(1, "現在ランクを選択してください"),
  peak_rank: z.string().min(1, "最高ランクを選択してください"),
  region: z.string().min(1, "活動地域を選択してください"),
  activity_time: z.array(z.string()),
  experience: z.string().optional(),
  premier: z.string().optional(),
  agents: z.array(z.string()),
  description: z.string().max(1000, "1000文字以内").optional(),
  conditions: z.string().max(500, "500文字以内").optional(),
  discord: z.string().max(100).optional(),
  twitter: z.string().max(100).optional(),
  deadline: z.string().optional(),
  is_public: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

const inputCls = "w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-slate-600 outline-none focus:border-brand-500 transition-colors";
const selectCls = "w-full rounded-xl border border-white/10 bg-slate-800 px-4 py-3 text-sm text-white outline-none focus:border-brand-500 transition-colors";
const labelCls = "mb-1.5 block text-sm font-medium text-slate-300";
const errCls = "mt-1 text-xs text-red-400";

function CheckboxGroup({
  options, value, onChange, cols = 3,
}: { options: string[]; value: string[]; onChange: (v: string[]) => void; cols?: number }) {
  const toggle = (opt: string) =>
    onChange(value.includes(opt) ? value.filter((x) => x !== opt) : [...value, opt]);
  return (
    <div className={cn("grid gap-2", cols === 2 ? "grid-cols-2" : "grid-cols-3")}>
      {options.map((opt) => (
        <label key={opt} className={cn(
          "flex cursor-pointer items-center gap-2.5 rounded-xl border p-3 text-sm transition-colors",
          value.includes(opt)
            ? "border-brand-500/50 bg-brand-500/10 text-brand-300"
            : "border-white/8 text-slate-400 hover:border-white/15 hover:text-white",
        )}>
          <div className={cn(
            "h-4 w-4 flex-shrink-0 rounded border-2 transition-colors flex items-center justify-center",
            value.includes(opt) ? "border-brand-500 bg-brand-500" : "border-slate-600",
          )}>
            {value.includes(opt) && <span className="text-[9px] text-white font-bold">✓</span>}
          </div>
          <input type="checkbox" className="sr-only" checked={value.includes(opt)} onChange={() => toggle(opt)} />
          <span className="font-medium">{opt}</span>
        </label>
      ))}
    </div>
  );
}

function RadioGroup({
  options, value, onChange,
}: { options: { value: string; label: string }[]; value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => (
        <label key={opt.value} className={cn(
          "flex cursor-pointer items-center gap-2 rounded-xl border px-4 py-2.5 text-sm transition-colors",
          value === opt.value
            ? "border-brand-500/50 bg-brand-500/10 text-brand-300"
            : "border-white/8 text-slate-400 hover:border-white/15 hover:text-white",
        )}>
          <input type="radio" className="sr-only" checked={value === opt.value} onChange={() => onChange(opt.value)} />
          <div className={cn("h-3.5 w-3.5 flex-shrink-0 rounded-full border-2 transition-colors",
            value === opt.value ? "border-brand-500 bg-brand-500" : "border-slate-600")} />
          <span className="font-medium">{opt.label}</span>
        </label>
      ))}
    </div>
  );
}

interface LFTFormProps {
  defaultValues?: Partial<LFTPost> & { player_name?: string };
  onSubmit: (data: LFTCreateInput) => Promise<void>;
  isSubmitting: boolean;
  error?: string;
  isEdit?: boolean;
}

export function LFTForm({ defaultValues, onSubmit, isSubmitting, error, isEdit }: LFTFormProps) {
  const { register, handleSubmit, control, watch, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      status: (defaultValues?.status as "open" | "negotiating" | "closed") ?? "open",
      roles: defaultValues?.roles ?? [],
      current_rank: defaultValues?.current_rank ?? "",
      peak_rank: defaultValues?.peak_rank ?? "",
      region: defaultValues?.region ?? "",
      activity_time: defaultValues?.activity_time ?? [],
      experience: defaultValues?.experience ?? "",
      premier: defaultValues?.premier ?? "",
      agents: defaultValues?.agents ?? [],
      description: defaultValues?.description ?? "",
      conditions: defaultValues?.conditions ?? "",
      discord: defaultValues?.discord ?? "",
      twitter: defaultValues?.twitter ?? "",
      deadline: defaultValues?.deadline ?? "",
      is_public: defaultValues?.is_public ?? true,
    },
  });

  const descLen = watch("description")?.length ?? 0;
  const condLen = watch("conditions")?.length ?? 0;

  const submit = handleSubmit(async (values) => {
    await onSubmit({
      ...values,
      experience: values.experience || undefined,
      premier: values.premier || undefined,
      description: values.description || undefined,
      conditions: values.conditions || undefined,
      discord: values.discord || undefined,
      twitter: values.twitter || undefined,
      deadline: values.deadline || undefined,
    });
  });

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="mb-6 flex items-center gap-2 text-sm text-slate-400">
        <Link href="/scout" className="hover:text-white">Scout</Link>
        <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
        <Link href="/scout/lft" className="hover:text-white">LFT</Link>
        <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
        <span className="text-white">{isEdit ? "編集" : "作成"}</span>
      </div>

      <div className="mb-6 flex items-center gap-3">
        <div className="rounded-2xl bg-purple-500/10 p-3">
          <Search className="h-6 w-6 text-purple-400" />
        </div>
        <div>
          <h1 className="text-xl font-black text-white">チームを探す (LFT)</h1>
          {defaultValues?.player_name && (
            <p className="text-sm text-slate-500">{defaultValues.player_name}</p>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />{error}
        </div>
      )}

      <form onSubmit={submit} className="space-y-5">
        {/* 基本情報 */}
        <div className="rounded-2xl border border-white/10 bg-slate-900 p-5 space-y-4">
          <h2 className="text-sm font-bold text-white">基本情報</h2>
          <div>
            <label className={labelCls}>募集状況</label>
            <Controller name="status" control={control} render={({ field }) => (
              <RadioGroup
                options={[
                  { value: "open", label: "募集中" },
                  { value: "negotiating", label: "交渉中" },
                  { value: "closed", label: "募集停止" },
                ]}
                value={field.value}
                onChange={field.onChange}
              />
            )} />
          </div>
        </div>

        {/* スキル・ランク */}
        <div className="rounded-2xl border border-white/10 bg-slate-900 p-5 space-y-5">
          <h2 className="text-sm font-bold text-white">スキル情報</h2>

          <div>
            <label className={labelCls}>希望ロール <span className="text-red-400">*</span></label>
            <Controller name="roles" control={control} render={({ field }) => (
              <CheckboxGroup options={ROLES} value={field.value} onChange={field.onChange} cols={3} />
            )} />
            {errors.roles && <p className={errCls}>{errors.roles.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>現在ランク <span className="text-red-400">*</span></label>
              <select {...register("current_rank")} className={selectCls}>
                <option value="">選択してください</option>
                {RANKS.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
              {errors.current_rank && <p className={errCls}>{errors.current_rank.message}</p>}
            </div>
            <div>
              <label className={labelCls}>最高ランク <span className="text-red-400">*</span></label>
              <select {...register("peak_rank")} className={selectCls}>
                <option value="">選択してください</option>
                {RANKS.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
              {errors.peak_rank && <p className={errCls}>{errors.peak_rank.message}</p>}
            </div>
          </div>

          {/* エージェント選択 */}
          <div>
            <label className={labelCls}>メインエージェント</label>
            <Controller name="agents" control={control} render={({ field }) => (
              <div className="space-y-3">
                {VALORANT_AGENTS.map((group) => (
                  <div key={group.role}>
                    <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-600">{group.role}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {group.agents.map((agent) => (
                        <button
                          key={agent}
                          type="button"
                          onClick={() => {
                            const next = field.value.includes(agent)
                              ? field.value.filter((a) => a !== agent)
                              : [...field.value, agent];
                            field.onChange(next);
                          }}
                          className={cn(
                            "rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors",
                            field.value.includes(agent)
                              ? "border-brand-500/50 bg-brand-500/10 text-brand-300"
                              : "border-white/8 text-slate-400 hover:border-white/20 hover:text-white",
                          )}
                        >
                          {agent}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )} />
          </div>
        </div>

        {/* 活動スタイル */}
        <div className="rounded-2xl border border-white/10 bg-slate-900 p-5 space-y-5">
          <h2 className="text-sm font-bold text-white">活動スタイル</h2>

          <div>
            <label className={labelCls}>活動地域 <span className="text-red-400">*</span></label>
            <select {...register("region")} className={selectCls}>
              <option value="">選択してください</option>
              {REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
            {errors.region && <p className={errCls}>{errors.region.message}</p>}
          </div>

          <div>
            <label className={labelCls}>活動時間</label>
            <Controller name="activity_time" control={control} render={({ field }) => (
              <CheckboxGroup options={ACTIVITY_TIMES} value={field.value} onChange={field.onChange} cols={3} />
            )} />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>大会経験</label>
              <Controller name="experience" control={control} render={({ field }) => (
                <RadioGroup
                  options={[
                    { value: "none", label: "なし" },
                    { value: "some", label: "少しあり" },
                    { value: "many", label: "多数あり" },
                  ]}
                  value={field.value ?? ""}
                  onChange={field.onChange}
                />
              )} />
            </div>
            <div>
              <label className={labelCls}>Premier経験</label>
              <Controller name="premier" control={control} render={({ field }) => (
                <RadioGroup
                  options={[
                    { value: "none", label: "なし" },
                    { value: "yes", label: "あり" },
                  ]}
                  value={field.value ?? ""}
                  onChange={field.onChange}
                />
              )} />
            </div>
          </div>
        </div>

        {/* 自己PR・希望条件 */}
        <div className="rounded-2xl border border-white/10 bg-slate-900 p-5 space-y-4">
          <h2 className="text-sm font-bold text-white">自己PR・希望条件</h2>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className={labelCls.replace("mb-1.5 ", "")}>自己PR</label>
              <span className={cn("text-xs", descLen > 900 ? "text-yellow-400" : "text-slate-600")}>{descLen}/1000</span>
            </div>
            <textarea {...register("description")} rows={5} className={cn(inputCls, "resize-none")}
              placeholder="プレイスタイル、強み、意気込みなどを自由に書いてください" />
            {errors.description && <p className={errCls}>{errors.description.message}</p>}
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className={labelCls.replace("mb-1.5 ", "")}>希望条件</label>
              <span className={cn("text-xs", condLen > 450 ? "text-yellow-400" : "text-slate-600")}>{condLen}/500</span>
            </div>
            <textarea {...register("conditions")} rows={3} className={cn(inputCls, "resize-none")}
              placeholder="・週4以上活動希望&#10;・競技志向のチーム希望&#10;・VC必須" />
            {errors.conditions && <p className={errCls}>{errors.conditions.message}</p>}
          </div>
        </div>

        {/* 連絡先・その他 */}
        <div className="rounded-2xl border border-white/10 bg-slate-900 p-5 space-y-4">
          <h2 className="text-sm font-bold text-white">連絡先・その他</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Discord（任意）</label>
              <input {...register("discord")} className={inputCls} placeholder="username" />
            </div>
            <div>
              <label className={labelCls}>X / Twitter（任意）</label>
              <input {...register("twitter")} className={inputCls} placeholder="@username" />
            </div>
          </div>
          <div>
            <label className={labelCls}>募集期限（任意）</label>
            <input type="date" {...register("deadline")} className={cn(inputCls, "appearance-none")} />
          </div>
        </div>

        {/* 公開設定 */}
        <div className="rounded-2xl border border-white/10 bg-slate-900 p-5">
          <h2 className="mb-3 text-sm font-bold text-white">公開設定</h2>
          <div className="flex flex-col gap-2">
            {[
              { value: true, label: "公開", desc: "スカウト・チーム担当者が検索できる" },
              { value: false, label: "非公開", desc: "URLを知っている人のみ閲覧可能" },
            ].map(({ value, label, desc }) => {
              const currentVal = watch("is_public");
              return (
                <label key={String(value)} className={cn(
                  "flex cursor-pointer items-center gap-3 rounded-xl border p-3.5 transition-colors",
                  currentVal === value ? "border-brand-500/50 bg-brand-500/10" : "border-white/8 hover:border-white/15",
                )}>
                  <Controller name="is_public" control={control} render={({ field }) => (
                    <input type="radio" className="sr-only" checked={field.value === value} onChange={() => field.onChange(value)} />
                  )} />
                  <div className={cn("h-4 w-4 flex-shrink-0 rounded-full border-2 transition-colors",
                    currentVal === value ? "border-brand-500 bg-brand-500" : "border-slate-600")} />
                  <div>
                    <p className={cn("text-sm font-semibold", currentVal === value ? "text-brand-300" : "text-slate-300")}>{label}</p>
                    <p className="text-xs text-slate-500">{desc}</p>
                  </div>
                </label>
              );
            })}
          </div>
        </div>

        <div className="flex gap-3 pb-4">
          <button type="submit" disabled={isSubmitting}
            className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-brand-500 py-3.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-40 transition-colors">
            {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {isEdit ? "変更を保存" : "LFTを登録"}
          </button>
          <Link href="/scout/lft"
            className="rounded-xl border border-white/10 px-6 py-3.5 text-sm text-slate-400 hover:text-white transition-colors">
            キャンセル
          </Link>
        </div>
      </form>
    </div>
  );
}
