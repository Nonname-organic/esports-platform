"use client";

import { useRouter } from "next/navigation";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Shield, AlertCircle } from "lucide-react";
import { useCreateTeam } from "@/features/teams/hooks/use-teams";
import { ImageUpload } from "@/components/image-upload";
import { cn } from "@/lib/utils";
import type { GameType } from "@/types/tournament";

const GAMES: { value: GameType; label: string }[] = [
  { value: "VALORANT", label: "VALORANT" },
  { value: "LOL", label: "League of Legends" },
  { value: "APEX", label: "Apex Legends" },
  { value: "CS2", label: "CS2" },
  { value: "OVERWATCH", label: "Overwatch 2" },
];

const schema = z.object({
  name: z.string().min(2, "2文字以上").max(100, "100文字以内"),
  tag: z.string().min(2, "2文字以上").max(10, "10文字以内").regex(/^[A-Za-z0-9]+$/, "英数字のみ"),
  game: z.enum(["VALORANT", "LOL", "APEX", "CS2", "OVERWATCH"] as const),
  description: z.string().max(1000).optional(),
  country: z.string().max(100).optional(),
  logo_url: z.string().optional(),
  banner_url: z.string().optional(),
  twitter_handle: z.string().max(50).optional(),
});

type FormValues = z.infer<typeof schema>;

export default function TeamCreatePage() {
  const router = useRouter();
  const createTeam = useCreateTeam();

  const {
    register, handleSubmit, control, watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { game: "VALORANT", logo_url: "", banner_url: "" },
  });

  const selectedGame = watch("game");

  const inputCls = (err?: boolean) => cn(
    "w-full rounded-xl border bg-white/5 px-4 py-3 text-sm text-white placeholder-slate-600 outline-none transition-colors",
    err ? "border-red-500/50" : "border-white/10 focus:border-brand-500",
  );

  const onSubmit = handleSubmit(async (values) => {
    const res = await createTeam.mutateAsync({
      ...values,
      logo_url: values.logo_url || undefined,
      banner_url: values.banner_url || undefined,
      description: values.description || undefined,
      country: values.country || undefined,
      twitter_handle: values.twitter_handle || undefined,
    });
    // 作成後はチーム管理画面（メンバー管理）へ
    router.push(`/teams/${res.data.id}/members`);
  });

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <div className="mb-8 flex items-center gap-3">
        <div className="rounded-2xl bg-brand-500/10 p-3">
          <Shield className="h-7 w-7 text-brand-400" />
        </div>
        <div>
          <h1 className="text-2xl font-black text-white">チームを作成</h1>
          <p className="text-sm text-slate-500">あなたが作成したチームのオーナーになります</p>
        </div>
      </div>

      <form onSubmit={onSubmit} className="space-y-5">
        {createTeam.isError && (
          <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            {createTeam.error instanceof Error ? createTeam.error.message : "作成に失敗しました"}
          </div>
        )}

        {/* 基本情報 */}
        <div className="rounded-2xl border border-white/10 bg-slate-900 p-5 space-y-4">
          <h2 className="text-sm font-bold text-white">基本情報</h2>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-400">チーム名 <span className="text-red-400">*</span></label>
            <input {...register("name")} className={inputCls(!!errors.name)} placeholder="Team Awesome" />
            {errors.name && <p className="mt-1 text-xs text-red-400">{errors.name.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-400">タグ <span className="text-red-400">*</span></label>
              <input
                {...register("tag")}
                className={inputCls(!!errors.tag)}
                placeholder="AWE"
                onChange={(e) => { e.target.value = e.target.value.toUpperCase(); register("tag").onChange(e); }}
              />
              {errors.tag && <p className="mt-1 text-xs text-red-400">{errors.tag.message}</p>}
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-400">ゲーム <span className="text-red-400">*</span></label>
              <select {...register("game")} className={cn(inputCls(), "bg-slate-800")}>
                {GAMES.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-400">説明</label>
            <textarea {...register("description")} rows={3} className={inputCls()} placeholder="チームの紹介、活動方針など..." />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-400">国・地域</label>
            <input {...register("country")} className={inputCls()} placeholder="Japan" />
          </div>
        </div>

        {/* ブランディング */}
        <div className="rounded-2xl border border-white/10 bg-slate-900 p-5 space-y-5">
          <h2 className="text-sm font-bold text-white">ブランディング</h2>

          <div className="flex gap-5">
            {/* ロゴ */}
            <Controller name="logo_url" control={control} render={({ field }) => (
              <ImageUpload
                value={field.value ?? ""}
                onChange={field.onChange}
                purpose="team_logo"
                label="チームロゴ"
                aspectRatio="square"
              />
            )} />

            <div className="flex-1 space-y-4">
              {/* バナー */}
              <Controller name="banner_url" control={control} render={({ field }) => (
                <ImageUpload
                  value={field.value ?? ""}
                  onChange={field.onChange}
                  purpose="team_banner"
                  label="バナー画像"
                  aspectRatio="banner"
                  className="w-full"
                />
              )} />

              {/* Twitter */}
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-400">Twitter (@なし)</label>
                <input {...register("twitter_handle")} className={inputCls()} placeholder="teamhandle" />
              </div>
            </div>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={isSubmitting || createTeam.isPending}
            className="flex-1 rounded-xl bg-brand-500 py-3 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-40 transition-colors"
          >
            {isSubmitting || createTeam.isPending ? "作成中..." : "チームを作成する"}
          </button>
          <button type="button" onClick={() => router.back()}
            className="rounded-xl border border-white/10 px-6 py-3 text-sm text-slate-400 hover:text-white transition-colors">
            キャンセル
          </button>
        </div>
      </form>
    </div>
  );
}
