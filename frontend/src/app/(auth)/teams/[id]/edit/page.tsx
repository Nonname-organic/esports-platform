"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Settings, AlertCircle, Loader2 } from "lucide-react";
import { useTeam, useUpdateTeam, useDeleteTeam } from "@/features/teams/hooks/use-teams";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth-store";

const schema = z.object({
  name: z.string().min(2).max(100),
  tag: z.string().min(2).max(10).regex(/^[A-Za-z0-9]+$/),
  description: z.string().max(1000).optional(),
  country: z.string().max(100).optional(),
  logo_url: z.string().url().optional().or(z.literal("")),
  banner_url: z.string().url().optional().or(z.literal("")),
  twitter_handle: z.string().max(50).optional(),
});

type FormValues = z.infer<typeof schema>;

export default function TeamEditPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const { data: team, isLoading } = useTeam(id);
  const updateTeam = useUpdateTeam(id);
  const deleteTeam = useDeleteTeam();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  useEffect(() => {
    if (team) reset({
      name: team.name,
      tag: team.tag,
      description: team.description ?? "",
      country: team.country ?? "",
      logo_url: team.logo_url ?? "",
      banner_url: team.banner_url ?? "",
      twitter_handle: (team as any).twitter_handle ?? "",
    });
  }, [team, reset]);

  const inputClass = (hasError?: boolean) =>
    cn(
      "w-full rounded-lg border bg-white/5 px-3 py-2.5 text-sm text-white placeholder-slate-600 outline-none transition-colors",
      hasError ? "border-red-500/50" : "border-white/10 focus:border-brand-500",
    );

  const onSubmit = handleSubmit(async (values) => {
    await updateTeam.mutateAsync({
      ...values,
      logo_url: values.logo_url || undefined,
      banner_url: values.banner_url || undefined,
    });
    router.push(`/teams/${id}`);
  });

  const handleDelete = async () => {
    if (!confirm("チームを削除しますか？この操作は取り消せません。")) return;
    await deleteTeam.mutateAsync(id);
    router.push("/dashboard");
  };

  if (isLoading) return (
    <div className="flex h-64 items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-brand-500" />
    </div>
  );

  if (!team) return <div className="p-8 text-center text-slate-400">チームが見つかりません</div>;

  const isOwner = user?.id === String(team.id) || user?.role === "admin";

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="mb-6 flex items-center gap-3">
        <div className="rounded-xl bg-brand-500/10 p-2">
          <Settings className="h-6 w-6 text-brand-400" />
        </div>
        <div>
          <h1 className="text-xl font-black text-white">チーム設定</h1>
          <p className="text-sm text-slate-500">{team.name}</p>
        </div>
      </div>

      <form onSubmit={onSubmit} className="space-y-5">
        {updateTeam.isError && (
          <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            <AlertCircle className="h-4 w-4" />
            {updateTeam.error instanceof Error ? updateTeam.error.message : "更新に失敗しました"}
          </div>
        )}

        <div className="rounded-xl border border-white/10 bg-slate-900 p-5 space-y-4">
          <h2 className="text-sm font-bold text-white">基本情報</h2>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-500">チーム名</label>
            <input {...register("name")} className={inputClass(!!errors.name)} />
            {errors.name && <p className="mt-1 text-xs text-red-400">{errors.name.message}</p>}
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-500">タグ</label>
            <input {...register("tag")} className={inputClass(!!errors.tag)} />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-500">説明</label>
            <textarea {...register("description")} rows={3} className={inputClass()} />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-500">国・地域</label>
            <input {...register("country")} className={inputClass()} />
          </div>
        </div>

        <div className="rounded-xl border border-white/10 bg-slate-900 p-5 space-y-4">
          <h2 className="text-sm font-bold text-white">ブランディング</h2>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-500">ロゴURL</label>
            <input {...register("logo_url")} className={inputClass(!!errors.logo_url)} />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-500">バナーURL</label>
            <input {...register("banner_url")} className={inputClass(!!errors.banner_url)} />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-500">Twitter</label>
            <input {...register("twitter_handle")} className={inputClass()} placeholder="@なし" />
          </div>
        </div>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex-1 rounded-xl bg-brand-500 py-3 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-40 transition-colors"
          >
            {isSubmitting ? "保存中..." : "変更を保存"}
          </button>
          <button type="button" onClick={() => router.back()} className="rounded-xl border border-white/10 px-5 py-3 text-sm text-slate-400 hover:text-white transition-colors">
            キャンセル
          </button>
        </div>

        {/* 危険な操作 */}
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-5">
          <h2 className="mb-3 text-sm font-bold text-red-400">危険な操作</h2>
          <p className="mb-3 text-xs text-slate-500">チームを削除すると全メンバーが脱退し、データは復元できません。</p>
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleteTeam.isPending}
            className="rounded-lg border border-red-500/30 px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-50"
          >
            {deleteTeam.isPending ? "削除中..." : "チームを削除する"}
          </button>
        </div>
      </form>
    </div>
  );
}
