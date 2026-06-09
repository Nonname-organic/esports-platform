"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  ClipboardList, Plus, ChevronRight, Users, Shield, Send, Trash2, X, AlertCircle,
} from "lucide-react";
import {
  useRecruitment, useCreateRecruitment, useDeleteRecruitment, useApply,
} from "@/features/scout/hooks/use-scout";
import { useAuthStore } from "@/store/auth-store";
import { cn, getGameColor, formatDate } from "@/lib/utils";
import type { RecruitmentPost } from "@/features/scout/api/scout-api";

const GAMES = ["VALORANT", "APEX", "CS2", "LOL", "OVERWATCH"];

const createSchema = z.object({
  post_type: z.enum(["team_seeks", "player_seeks"]),
  game: z.string().min(1),
  title: z.string().min(2, "2文字以上").max(200),
  description: z.string().max(2000).optional(),
  min_rank: z.string().optional(),
});
type CreateForm = z.infer<typeof createSchema>;

export default function RecruitmentBoardPage() {
  const user = useAuthStore((s) => s.user);
  const [tab, setTab] = useState<"all" | "team_seeks" | "player_seeks">("all");
  const [showForm, setShowForm] = useState(false);

  const { data: posts, isLoading } = useRecruitment(
    tab === "all" ? undefined : { post_type: tab }
  );
  const createPost = useCreateRecruitment();
  const deletePost = useDeleteRecruitment();
  const apply = useApply();

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
    defaultValues: { post_type: "team_seeks", game: "VALORANT" },
  });

  const onCreate = handleSubmit(async (data) => {
    await createPost.mutateAsync(data);
    reset();
    setShowForm(false);
  });

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/scout" className="text-slate-500 hover:text-white transition-colors">Scout</Link>
          <ChevronRight className="h-4 w-4 text-slate-600" />
          <h1 className="text-xl font-black text-white">Recruitment Board</h1>
        </div>
        <button onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 rounded-lg bg-brand-500/10 px-4 py-2 text-sm font-semibold text-brand-400 hover:bg-brand-500/20 transition-colors">
          <Plus className="h-4 w-4" />募集を作成
        </button>
      </div>

      {/* 作成フォーム */}
      {showForm && (
        <form onSubmit={onCreate} className="mb-5 space-y-4 rounded-2xl border border-brand-500/30 bg-slate-900 p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white">新規募集</h2>
            <button type="button" onClick={() => setShowForm(false)} className="text-slate-500 hover:text-white"><X className="h-4 w-4" /></button>
          </div>
          {createPost.isError && (
            <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">
              <AlertCircle className="h-3.5 w-3.5" />作成に失敗しました
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <select {...register("post_type")} className="rounded-lg border border-white/10 bg-slate-800 px-3 py-2.5 text-sm text-white outline-none focus:border-brand-500">
              <option value="team_seeks">チームが選手を募集</option>
              <option value="player_seeks">選手がチームを募集</option>
            </select>
            <select {...register("game")} className="rounded-lg border border-white/10 bg-slate-800 px-3 py-2.5 text-sm text-white outline-none focus:border-brand-500">
              {GAMES.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </div>
          <input {...register("title")} placeholder="募集タイトル"
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder-slate-600 outline-none focus:border-brand-500" />
          {errors.title && <p className="text-xs text-red-400">{errors.title.message}</p>}
          <textarea {...register("description")} rows={3} placeholder="詳細・条件など"
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder-slate-600 outline-none focus:border-brand-500" />
          <button type="submit" disabled={isSubmitting || createPost.isPending}
            className="rounded-lg bg-brand-500 px-5 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-40 transition-colors">
            {isSubmitting || createPost.isPending ? "作成中..." : "募集を掲載"}
          </button>
        </form>
      )}

      {/* タブ */}
      <div className="mb-5 flex gap-1 rounded-xl border border-white/10 bg-slate-900 p-1">
        {[
          { value: "all", label: "すべて" },
          { value: "team_seeks", label: "選手募集" },
          { value: "player_seeks", label: "チーム募集" },
        ].map((t) => (
          <button key={t.value} onClick={() => setTab(t.value as typeof tab)}
            className={cn("flex-1 rounded-lg px-3 py-2 text-xs font-semibold transition-colors",
              tab === t.value ? "bg-brand-500 text-white" : "text-slate-500 hover:text-white")}>
            {t.label}
          </button>
        ))}
      </div>

      {/* リスト */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-28 animate-pulse rounded-xl bg-white/5" />)}
        </div>
      ) : !posts || posts.length === 0 ? (
        <div className="flex flex-col items-center py-20 text-center">
          <ClipboardList className="mb-3 h-12 w-12 text-slate-700" />
          <p className="text-sm text-slate-500">募集がありません</p>
        </div>
      ) : (
        <div className="space-y-3">
          {posts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              isOwner={user?.id === post.author_id}
              onApply={() => apply.mutate({ post_id: post.id, kind: "apply" })}
              onDelete={() => deletePost.mutate(post.id)}
              applying={apply.isPending}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function PostCard({ post, isOwner, onApply, onDelete, applying }: {
  post: RecruitmentPost; isOwner: boolean; onApply: () => void; onDelete: () => void; applying: boolean;
}) {
  const isTeamSeeks = post.post_type === "team_seeks";
  return (
    <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
      <div className="mb-2 flex items-center gap-2">
        <span className={cn("flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold",
          isTeamSeeks ? "bg-brand-500/10 text-brand-400" : "bg-purple-500/10 text-purple-400")}>
          {isTeamSeeks ? <Shield className="h-3 w-3" /> : <Users className="h-3 w-3" />}
          {isTeamSeeks ? "選手募集" : "チーム募集"}
        </span>
        <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-bold", getGameColor(post.game))}>{post.game}</span>
        <span className="ml-auto text-[10px] text-slate-600">{formatDate(post.created_at)}</span>
      </div>
      <h3 className="font-bold text-white">{post.title}</h3>
      {post.description && <p className="mt-1 text-sm text-slate-400 line-clamp-2">{post.description}</p>}
      <div className="mt-3 flex items-center justify-between">
        <span className="text-xs text-slate-500">{post.application_count}件の応募</span>
        {isOwner ? (
          <button onClick={onDelete}
            className="flex items-center gap-1.5 rounded-lg border border-red-500/20 px-3 py-1.5 text-xs text-red-400 hover:bg-red-500/10 transition-colors">
            <Trash2 className="h-3.5 w-3.5" />削除
          </button>
        ) : (
          <button onClick={onApply} disabled={applying}
            className="flex items-center gap-1.5 rounded-lg bg-brand-500/10 px-4 py-1.5 text-xs font-semibold text-brand-400 hover:bg-brand-500/20 disabled:opacity-50 transition-colors">
            <Send className="h-3.5 w-3.5" />応募する
          </button>
        )}
      </div>
    </div>
  );
}
