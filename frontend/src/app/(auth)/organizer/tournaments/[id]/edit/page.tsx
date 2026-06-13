"use client";

import { use, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, ChevronRight, Loader2, Save } from "lucide-react";
import { tournamentApi } from "@/features/tournaments/api/tournament-api";
import { cn } from "@/lib/utils";

function toLocalInput(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}
function toIso(local?: string): string | undefined {
  if (!local) return undefined;
  const d = new Date(local);
  return isNaN(d.getTime()) ? undefined : d.toISOString();
}

interface FormValues {
  name: string;
  description: string;
  max_teams: number | string;
  prize_pool: number | string;
  registration_start_at: string;
  registration_end_at: string;
  start_at: string;
  end_at: string;
  is_public: boolean;
}

export default function TournamentEditPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const qc = useQueryClient();

  const { data: t, isLoading } = useQuery({
    queryKey: ["tournament", id],
    queryFn: () => tournamentApi.get(id),
    select: (res) => res.data,
  });

  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm<FormValues>();

  const update = useMutation({
    mutationFn: (data: Parameters<typeof tournamentApi.update>[1]) => tournamentApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tournament", id] });
      router.push(`/organizer/tournaments/${id}`);
    },
  });

  useEffect(() => {
    if (t) reset({
      name: t.name,
      description: t.description ?? "",
      max_teams: t.max_teams ?? "",
      prize_pool: (t.prize_pool as number | null) ?? "",
      registration_start_at: toLocalInput(t.registration_start_at),
      registration_end_at: toLocalInput(t.registration_end_at),
      start_at: toLocalInput(t.start_at),
      end_at: toLocalInput(t.end_at),
      is_public: (t as { is_public?: boolean }).is_public ?? true,
    });
  }, [t, reset]);

  const onSubmit = handleSubmit((v) => {
    update.mutate({
      name: v.name || undefined,
      description: v.description || undefined,
      max_teams: v.max_teams ? Number(v.max_teams) : undefined,
      prize_pool: v.prize_pool !== "" && v.prize_pool != null ? Number(v.prize_pool) : undefined,
      registration_start_at: toIso(v.registration_start_at),
      registration_end_at: toIso(v.registration_end_at),
      start_at: toIso(v.start_at),
      end_at: toIso(v.end_at),
      is_public: v.is_public,
    });
  });

  const inputCls = "w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder-slate-600 outline-none focus:border-brand-500 transition-colors";

  if (isLoading) return (
    <div className="flex h-64 items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-brand-500" />
    </div>
  );
  if (!t) return <div className="p-8 text-center text-slate-400">大会が見つかりません</div>;

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      {/* パンくず */}
      <nav className="mb-4 flex items-center gap-2 text-sm text-slate-400">
        <Link href={`/organizer/tournaments/${id}`} className="hover:text-white transition-colors">{t.name}</Link>
        <ChevronRight className="h-3.5 w-3.5" />
        <span className="text-white">大会情報を編集</span>
      </nav>

      <form onSubmit={onSubmit} className="space-y-5">
        {update.isError && (
          <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            <AlertCircle className="h-4 w-4" />
            {update.error instanceof Error ? update.error.message : "更新に失敗しました"}
          </div>
        )}

        {/* 基本情報 */}
        <div className="rounded-xl border border-white/10 bg-slate-900 p-5 space-y-4">
          <h2 className="text-sm font-bold text-white">基本情報</h2>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-400">大会名</label>
            <input {...register("name")} className={inputCls} placeholder="大会名" />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-400">説明</label>
            <textarea {...register("description")} rows={4} className={inputCls} placeholder="大会の説明..." />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-400">最大チーム数</label>
              <input type="number" min={2} max={256} {...register("max_teams")} className={inputCls} />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-400">賞金総額</label>
              <input type="number" min={0} {...register("prize_pool")} className={inputCls} placeholder="0" />
            </div>
          </div>
        </div>

        {/* スケジュール */}
        <div className="rounded-xl border border-white/10 bg-slate-900 p-5 space-y-4">
          <h2 className="text-sm font-bold text-white">スケジュール</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {[
              { name: "registration_start_at" as const, label: "参加受付開始" },
              { name: "registration_end_at" as const, label: "参加受付終了" },
              { name: "start_at" as const, label: "大会開始" },
              { name: "end_at" as const, label: "大会終了" },
            ].map(({ name, label }) => (
              <div key={name}>
                <label className="mb-2 block text-sm font-medium text-slate-400">{label}</label>
                <input type="datetime-local" {...register(name)} className={cn(inputCls, "[color-scheme:dark]")} />
              </div>
            ))}
          </div>
        </div>

        {/* 公開設定 */}
        <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <label className="flex items-center gap-3 text-sm text-slate-300">
            <input type="checkbox" {...register("is_public")} className="h-4 w-4 rounded accent-brand-500" />
            一般公開する（大会一覧に表示）
          </label>
        </div>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={isSubmitting || update.isPending}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-brand-500 py-3 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-40 transition-colors"
          >
            <Save className="h-4 w-4" />
            {isSubmitting || update.isPending ? "保存中..." : "変更を保存"}
          </button>
          <Link href={`/organizer/tournaments/${id}`}
            className="rounded-xl border border-white/10 px-6 py-3 text-sm text-slate-400 hover:text-white transition-colors">
            キャンセル
          </Link>
        </div>
      </form>
    </div>
  );
}
