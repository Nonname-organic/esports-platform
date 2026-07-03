"use client";

import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Link from "next/link";
import { ChevronRight, AlertCircle, Loader2, Users } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LFPCreateInput, LFPPost } from "@/features/lfp/api/lfp-api";
import type { Team } from "@/types/team";

const ROLES = ["Duelist", "Initiator", "Controller", "Sentinel", "Flex", "IGL"];
const RANKS = ["Iron", "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Ascendant", "Immortal", "Radiant"];
const REGIONS = ["全国", "北海道", "東北", "関東", "中部", "関西", "中国", "四国", "九州", "海外", "オンラインのみ"];
const ACTIVITY_TIMES = ["平日昼", "平日夜", "土日昼", "土日夜", "不定期"];
const ACTIVITY_LEVELS = ["エンジョイ", "競技志向", "大会メイン", "Premierメイン"];
const TOURNAMENT_OPTIONS = ["Premier", "コミュニティ大会", "オフライン大会"];
const AGE_OPTIONS = ["制限なし", "高校生以上", "18歳以上"];

const schema = z.object({
  team_id: z.string().min(1, "チームを選択してください"),
  title: z.string().min(1, "タイトルは必須です").max(200, "200文字以内"),
  status: z.enum(["open", "paused", "closed"]),
  roles: z.array(z.string()).min(1, "ロールを1つ以上選択してください"),
  headcount: z.number().int().min(1).max(5),
  min_rank: z.string().min(1, "希望ランクは必須です"),
  region: z.string().min(1, "活動地域は必須です"),
  activity_time: z.array(z.string()),
  activity_level: z.string().optional(),
  tournaments: z.array(z.string()),
  age_requirement: z.string().optional(),
  description: z.string().max(500, "500文字以内").optional(),
  team_intro: z.string().max(1000, "1000文字以内").optional(),
  discord: z.string().max(100).optional(),
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

interface LFPFormProps {
  teams: Team[];
  defaultValues?: Partial<LFPPost>;
  onSubmit: (data: LFPCreateInput) => Promise<void>;
  isSubmitting: boolean;
  error?: string;
}

export function LFPForm({ teams, defaultValues, onSubmit, isSubmitting, error }: LFPFormProps) {
  const { register, handleSubmit, control, watch, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      team_id: defaultValues?.team_id ?? (teams.length === 1 ? teams[0].id : ""),
      title: defaultValues?.title ?? "",
      status: (defaultValues?.status as "open" | "paused" | "closed") ?? "open",
      roles: defaultValues?.roles ?? [],
      headcount: defaultValues?.headcount ?? 1,
      min_rank: defaultValues?.min_rank ?? "",
      region: defaultValues?.region ?? "",
      activity_time: defaultValues?.activity_time ?? [],
      activity_level: defaultValues?.activity_level ?? "",
      tournaments: defaultValues?.tournaments ?? [],
      age_requirement: defaultValues?.age_requirement ?? "",
      description: defaultValues?.description ?? "",
      team_intro: defaultValues?.team_intro ?? "",
      discord: defaultValues?.discord ?? "",
      deadline: defaultValues?.deadline ?? "",
      is_public: defaultValues?.is_public ?? true,
    },
  });

  const descLen = watch("description")?.length ?? 0;
  const introLen = watch("team_intro")?.length ?? 0;
  const isEdit = !!defaultValues?.id;

  const submit = handleSubmit(async (values) => {
    await onSubmit({
      ...values,
      activity_level: values.activity_level || undefined,
      age_requirement: values.age_requirement || undefined,
      description: values.description || undefined,
      team_intro: values.team_intro || undefined,
      discord: values.discord || undefined,
      deadline: values.deadline || undefined,
    });
  });

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      {/* パンくず */}
      <div className="mb-6 flex items-center gap-2 text-sm text-slate-400">
        <Link href="/scout" className="hover:text-white">Scout</Link>
        <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
        <Link href="/scout/lfp" className="hover:text-white">チーム募集</Link>
        <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
        <span className="text-white">{isEdit ? "編集" : "作成"}</span>
      </div>

      <div className="mb-6 flex items-center gap-3">
        <div className="rounded-2xl bg-brand-500/10 p-3">
          <Users className="h-6 w-6 text-brand-400" />
        </div>
        <div>
          <h1 className="text-xl font-black text-white">チームメンバー募集 (LFP)</h1>
          <p className="text-sm text-slate-500">一緒に戦うメンバーを募集しましょう</p>
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
            <label className={labelCls}>募集タイトル <span className="text-red-400">*</span></label>
            <input {...register("title")} className={inputCls} placeholder="例: Immortal以上のController募集" />
            {errors.title && <p className={errCls}>{errors.title.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>チーム <span className="text-red-400">*</span></label>
              <select {...register("team_id")} className={selectCls} disabled={teams.length === 1}>
                <option value="">チームを選択</option>
                {teams.map((t) => (
                  <option key={t.id} value={t.id}>{t.name} [{t.tag}]</option>
                ))}
              </select>
              {errors.team_id && <p className={errCls}>{errors.team_id.message}</p>}
            </div>
            <div>
              <label className={labelCls}>募集状況</label>
              <select {...register("status")} className={selectCls}>
                <option value="open">募集中</option>
                <option value="paused">一時停止</option>
                <option value="closed">募集終了</option>
              </select>
            </div>
          </div>
        </div>

        {/* 募集内容 */}
        <div className="rounded-2xl border border-white/10 bg-slate-900 p-5 space-y-5">
          <h2 className="text-sm font-bold text-white">募集内容</h2>

          <div>
            <label className={labelCls}>募集ロール <span className="text-red-400">*</span></label>
            <Controller name="roles" control={control} render={({ field }) => (
              <CheckboxGroup options={ROLES} value={field.value} onChange={field.onChange} cols={3} />
            )} />
            {errors.roles && <p className={errCls}>{errors.roles.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>募集人数 <span className="text-red-400">*</span></label>
              <select {...register("headcount", { valueAsNumber: true })} className={selectCls}>
                {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}名</option>)}
              </select>
            </div>
            <div>
              <label className={labelCls}>希望ランク（最低） <span className="text-red-400">*</span></label>
              <select {...register("min_rank")} className={selectCls}>
                <option value="">選択してください</option>
                {RANKS.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
              {errors.min_rank && <p className={errCls}>{errors.min_rank.message}</p>}
            </div>
          </div>

          <div>
            <label className={labelCls}>活動地域 <span className="text-red-400">*</span></label>
            <select {...register("region")} className={selectCls}>
              <option value="">選択してください</option>
              {REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
            {errors.region && <p className={errCls}>{errors.region.message}</p>}
          </div>
        </div>

        {/* 活動スタイル */}
        <div className="rounded-2xl border border-white/10 bg-slate-900 p-5 space-y-5">
          <h2 className="text-sm font-bold text-white">活動スタイル</h2>

          <div>
            <label className={labelCls}>活動時間</label>
            <Controller name="activity_time" control={control} render={({ field }) => (
              <CheckboxGroup options={ACTIVITY_TIMES} value={field.value} onChange={field.onChange} cols={3} />
            )} />
          </div>

          <div>
            <label className={labelCls}>活動レベル</label>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {ACTIVITY_LEVELS.map((lv) => {
                const currentVal = watch("activity_level");
                return (
                  <label key={lv} className={cn(
                    "flex cursor-pointer items-center gap-2 rounded-xl border p-3 text-sm transition-colors",
                    currentVal === lv
                      ? "border-brand-500/50 bg-brand-500/10 text-brand-300"
                      : "border-white/8 text-slate-400 hover:border-white/15",
                  )}>
                    <input type="radio" {...register("activity_level")} value={lv} className="sr-only" />
                    <div className={cn("h-3.5 w-3.5 flex-shrink-0 rounded-full border-2 transition-colors",
                      currentVal === lv ? "border-brand-500 bg-brand-500" : "border-slate-600")} />
                    <span className="font-medium text-xs">{lv}</span>
                  </label>
                );
              })}
            </div>
          </div>

          <div>
            <label className={labelCls}>大会参加予定</label>
            <Controller name="tournaments" control={control} render={({ field }) => (
              <CheckboxGroup options={TOURNAMENT_OPTIONS} value={field.value} onChange={field.onChange} cols={3} />
            )} />
          </div>

          <div>
            <label className={labelCls}>年齢条件</label>
            <div className="flex flex-wrap gap-2">
              {AGE_OPTIONS.map((opt) => {
                const currentVal = watch("age_requirement");
                return (
                  <label key={opt} className={cn(
                    "flex cursor-pointer items-center gap-2 rounded-xl border px-4 py-2.5 text-sm transition-colors",
                    currentVal === opt
                      ? "border-brand-500/50 bg-brand-500/10 text-brand-300"
                      : "border-white/8 text-slate-400 hover:border-white/15",
                  )}>
                    <input type="radio" {...register("age_requirement")} value={opt} className="sr-only" />
                    <div className={cn("h-3.5 w-3.5 rounded-full border-2 transition-colors",
                      currentVal === opt ? "border-brand-500 bg-brand-500" : "border-slate-600")} />
                    <span className="font-medium">{opt}</span>
                  </label>
                );
              })}
            </div>
          </div>
        </div>

        {/* テキスト情報 */}
        <div className="rounded-2xl border border-white/10 bg-slate-900 p-5 space-y-4">
          <h2 className="text-sm font-bold text-white">詳細情報</h2>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-sm font-medium text-slate-300">加入条件</label>
              <span className={cn("text-xs", descLen > 450 ? "text-yellow-400" : "text-slate-600")}>{descLen}/500</span>
            </div>
            <textarea {...register("description")} rows={4} className={cn(inputCls, "resize-none")}
              placeholder="・VC必須&#10;・報連相できる方&#10;・向上心ある方" />
            {errors.description && <p className={errCls}>{errors.description.message}</p>}
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-sm font-medium text-slate-300">チーム紹介</label>
              <span className={cn("text-xs", introLen > 900 ? "text-yellow-400" : "text-slate-600")}>{introLen}/1000</span>
            </div>
            <textarea {...register("team_intro")} rows={5} className={cn(inputCls, "resize-none")}
              placeholder="チームの雰囲気や目標を自由に書いてください..." />
            {errors.team_intro && <p className={errCls}>{errors.team_intro.message}</p>}
          </div>

          <div>
            <label className={labelCls}>Discord（任意）</label>
            <input {...register("discord")} className={inputCls} placeholder="username または サーバー招待リンク" />
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
              { value: true, label: "公開", desc: "誰でも検索・閲覧可能" },
              { value: false, label: "非公開", desc: "URLを知っている人のみ閲覧可能" },
            ].map(({ value, label, desc }) => {
              const currentVal = watch("is_public");
              return (
                <label key={String(value)} className={cn(
                  "flex cursor-pointer items-center gap-3 rounded-xl border p-3.5 transition-colors",
                  currentVal === value
                    ? "border-brand-500/50 bg-brand-500/10"
                    : "border-white/8 hover:border-white/15",
                )}>
                  <input type="radio" checked={currentVal === value}
                    onChange={() => {}} onClick={() => { }} className="sr-only" />
                  <Controller name="is_public" control={control} render={({ field }) => (
                    <input type="radio" value={String(value)} checked={field.value === value}
                      onChange={() => field.onChange(value)} className="sr-only" />
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

        {/* 送信ボタン */}
        <div className="flex gap-3 pb-4">
          <button type="submit" disabled={isSubmitting}
            className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-brand-500 py-3.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-40 transition-colors">
            {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {isEdit ? "変更を保存" : "募集を作成"}
          </button>
          <Link href="/scout/lfp"
            className="rounded-xl border border-white/10 px-6 py-3.5 text-sm text-slate-400 hover:text-white transition-colors">
            キャンセル
          </Link>
        </div>
      </form>
    </div>
  );
}
