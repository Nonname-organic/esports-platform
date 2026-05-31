"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Shield, AlertCircle } from "lucide-react";
import { useCreateTeam } from "@/features/teams/hooks/use-teams";
import { cn } from "@/lib/utils";
import type { GameType } from "@/types/tournament";

const GAMES: GameType[] = ["VALORANT", "LOL", "APEX", "CS2", "OVERWATCH"];

const schema = z.object({
  name: z.string().min(2, "2文字以上").max(100, "100文字以内"),
  tag: z.string().min(2, "2文字以上").max(10, "10文字以内").regex(/^[A-Za-z0-9]+$/, "英数字のみ"),
  game: z.enum(["VALORANT", "LOL", "APEX", "CS2", "OVERWATCH"] as const),
  description: z.string().max(1000).optional(),
  country: z.string().max(100).optional(),
  logo_url: z.string().url("正しいURLを入力してください").optional().or(z.literal("")),
  banner_url: z.string().url("正しいURLを入力してください").optional().or(z.literal("")),
  twitter_handle: z.string().max(50).optional(),
});

type FormValues = z.infer<typeof schema>;

function Field({ label, error, children, required }: {
  label: string; error?: string; children: React.ReactNode; required?: boolean;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-slate-400">
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      {children}
      {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
    </div>
  );
}

export default function TeamCreatePage() {
  const router = useRouter();
  const createTeam = useCreateTeam();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { game: "VALORANT" },
  });

  const onSubmit = handleSubmit(async (values) => {
    const data = {
      ...values,
      logo_url: values.logo_url || undefined,
      banner_url: values.banner_url || undefined,
      description: values.description || undefined,
      country: values.country || undefined,
      twitter_handle: values.twitter_handle || undefined,
    };
    const res = await createTeam.mutateAsync(data);
    router.push(`/teams/${res.data.id}`);
  });

  const inputClass = (hasError?: boolean) =>
    cn(
      "w-full rounded-lg border bg-white/5 px-3 py-2.5 text-sm text-white placeholder-slate-600 outline-none transition-colors",
      hasError ? "border-red-500/50 focus:border-red-500" : "border-white/10 focus:border-brand-500",
    );

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="mb-6 flex items-center gap-3">
        <div className="rounded-xl bg-brand-500/10 p-2">
          <Shield className="h-6 w-6 text-brand-400" />
        </div>
        <div>
          <h1 className="text-xl font-black text-white">チームを作成</h1>
          <p className="text-sm text-slate-500">あなたが作成したチームのオーナーになります</p>
        </div>
      </div>

      <form onSubmit={onSubmit} className="space-y-5">
        {createTeam.isError && (
          <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            {createTeam.error instanceof Error ? createTeam.error.message : "作成に失敗しました"}
          </div>
        )}

        <div className="rounded-xl border border-white/10 bg-slate-900 p-5 space-y-4">
          <h2 className="text-sm font-bold text-white">基本情報</h2>

          <Field label="チーム名" error={errors.name?.message} required>
            <input {...register("name")} className={inputClass(!!errors.name)} placeholder="Team Awesome" />
          </Field>

          <div className="grid grid-cols-2 gap-4">
            <Field label="タグ（略称）" error={errors.tag?.message} required>
              <input
                {...register("tag")}
                className={inputClass(!!errors.tag)}
                placeholder="AWE"
                onChange={(e) => {
                  e.target.value = e.target.value.toUpperCase();
                  register("tag").onChange(e);
                }}
              />
            </Field>

            <Field label="ゲーム" error={errors.game?.message} required>
              <select {...register("game")} className={inputClass(!!errors.game) + " bg-slate-800"}>
                {GAMES.map((g) => <option key={g} value={g}>{g}</option>)}
              </select>
            </Field>
          </div>

          <Field label="説明" error={errors.description?.message}>
            <textarea
              {...register("description")}
              rows={3}
              className={inputClass(!!errors.description)}
              placeholder="チームの説明..."
            />
          </Field>

          <Field label="国・地域" error={errors.country?.message}>
            <input {...register("country")} className={inputClass(!!errors.country)} placeholder="Japan" />
          </Field>
        </div>

        <div className="rounded-xl border border-white/10 bg-slate-900 p-5 space-y-4">
          <h2 className="text-sm font-bold text-white">ブランディング（任意）</h2>

          <Field label="ロゴURL" error={errors.logo_url?.message}>
            <input {...register("logo_url")} className={inputClass(!!errors.logo_url)} placeholder="https://example.com/logo.png" />
          </Field>

          <Field label="バナーURL" error={errors.banner_url?.message}>
            <input {...register("banner_url")} className={inputClass(!!errors.banner_url)} placeholder="https://example.com/banner.png" />
          </Field>

          <Field label="Twitter（@なし）" error={errors.twitter_handle?.message}>
            <input {...register("twitter_handle")} className={inputClass(!!errors.twitter_handle)} placeholder="teamhandle" />
          </Field>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={isSubmitting || createTeam.isPending}
            className="flex-1 rounded-xl bg-brand-500 py-3 text-sm font-bold text-white hover:bg-brand-600 transition-colors disabled:opacity-40"
          >
            {isSubmitting || createTeam.isPending ? "作成中..." : "チームを作成する"}
          </button>
          <button
            type="button"
            onClick={() => router.back()}
            className="rounded-xl border border-white/10 px-6 py-3 text-sm text-slate-400 hover:text-white transition-colors"
          >
            キャンセル
          </button>
        </div>
      </form>
    </div>
  );
}
