"use client";

import { use } from "react";
import { rankColor } from "@/lib/valorant";
import Link from "next/link";
import { ChevronRight, Shield, MapPin, Clock, Star, Users, Calendar, MessageSquare, Edit2, Trash2, Loader2 } from "lucide-react";
import { useLFP, useDeleteLFP } from "@/features/lfp/hooks/use-lfp";
import { useAuthStore } from "@/store/auth-store";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";


const STATUS_LABEL: Record<string, { label: string; cls: string }> = {
  open: { label: "募集中", cls: "bg-green-500/10 text-green-400 border-green-500/20" },
  paused: { label: "一時停止", cls: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20" },
  closed: { label: "募集終了", cls: "bg-white/5 text-slate-500 border-white/10" },
};

export default function LFPDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: post, isLoading } = useLFP(id);
  const user = useAuthStore((s) => s.user);
  const router = useRouter();
  const deleteLFP = useDeleteLFP();

  if (isLoading) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  if (!post) {
    return (
      <div className="flex flex-col items-center py-20 text-center">
        <p className="text-slate-400">募集が見つかりません</p>
        <Link href="/scout/lfp" className="mt-4 text-brand-400 hover:underline">一覧に戻る</Link>
      </div>
    );
  }

  const st = STATUS_LABEL[post.status] ?? STATUS_LABEL.open;
  const isOwner = user?.id === post.owner_id;

  const handleDelete = async () => {
    if (!confirm("この募集を削除しますか？")) return;
    await deleteLFP.mutateAsync(post.id);
    router.push("/scout/lfp");
  };

  const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <div className="rounded-2xl border border-white/10 bg-slate-900 p-5">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">{title}</h2>
      {children}
    </div>
  );

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      {/* パンくず */}
      <div className="mb-6 flex items-center gap-2 text-sm text-slate-400">
        <Link href="/scout" className="hover:text-white">Scout</Link>
        <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
        <Link href="/scout/lfp" className="hover:text-white">チーム募集</Link>
        <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
        <span className="truncate text-white">{post.title}</span>
      </div>

      {/* ヘッダー */}
      <div className="mb-5 rounded-2xl border border-white/10 bg-slate-900 p-5">
        <div className="flex items-start gap-4">
          <div className="h-14 w-14 flex-shrink-0 overflow-hidden rounded-xl border border-white/10 bg-slate-800 flex items-center justify-center">
            {post.team_logo_url
              ? <img src={post.team_logo_url} alt="" className="h-full w-full object-contain" />
              : <Shield className="h-7 w-7 text-slate-600" />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={cn("rounded-full border px-2.5 py-0.5 text-xs font-bold", st.cls)}>{st.label}</span>
              <Link href={`/teams/${post.team_id}`} className="text-sm text-slate-400 hover:text-white transition-colors">
                {post.team_name} [{post.team_tag}]
              </Link>
            </div>
            <h1 className="mt-1 text-xl font-black text-white">{post.title}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-500">
              <span className={cn("font-bold", rankColor(post.min_rank))}>{post.min_rank}〜</span>
              <span className="flex items-center gap-1"><Users className="h-3 w-3" />{post.headcount}名募集</span>
              {post.region && <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{post.region}</span>}
              {post.deadline && <span className="flex items-center gap-1"><Calendar className="h-3 w-3" />期限 {post.deadline}</span>}
            </div>
          </div>
          {isOwner && (
            <div className="flex gap-2 flex-shrink-0">
              <Link href={`/scout/lfp/${post.id}/edit`}
                className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:text-white transition-colors">
                <Edit2 className="h-3.5 w-3.5" /> 編集
              </Link>
              <button onClick={handleDelete} disabled={deleteLFP.isPending}
                className="flex items-center gap-1.5 rounded-lg bg-red-500/10 px-3 py-1.5 text-xs text-red-400 hover:bg-red-500/20 disabled:opacity-50 transition-colors">
                {deleteLFP.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />} 削除
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="space-y-4">
        {/* 募集ロール */}
        <Section title="募集ロール">
          <div className="flex flex-wrap gap-2">
            {post.roles.map((r) => (
              <span key={r} className="rounded-lg bg-brand-500/10 px-3 py-1.5 text-sm font-semibold text-brand-400">{r}</span>
            ))}
          </div>
        </Section>

        {/* 活動情報 */}
        <Section title="活動情報">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            {post.activity_level && (
              <div>
                <p className="text-xs text-slate-500 mb-1">活動レベル</p>
                <p className="text-sm font-semibold text-white">{post.activity_level}</p>
              </div>
            )}
            {post.activity_time.length > 0 && (
              <div>
                <p className="text-xs text-slate-500 mb-1">活動時間</p>
                <p className="text-sm text-white">{post.activity_time.join(" / ")}</p>
              </div>
            )}
            {post.age_requirement && (
              <div>
                <p className="text-xs text-slate-500 mb-1">年齢条件</p>
                <p className="text-sm text-white">{post.age_requirement}</p>
              </div>
            )}
            {post.tournaments.length > 0 && (
              <div>
                <p className="text-xs text-slate-500 mb-1">大会参加予定</p>
                <p className="text-sm text-white">{post.tournaments.join(" / ")}</p>
              </div>
            )}
          </div>
        </Section>

        {/* 加入条件 */}
        {post.description && (
          <Section title="加入条件">
            <p className="whitespace-pre-wrap text-sm text-slate-300 leading-relaxed">{post.description}</p>
          </Section>
        )}

        {/* チーム紹介 */}
        {post.team_intro && (
          <Section title="チーム紹介">
            <p className="whitespace-pre-wrap text-sm text-slate-300 leading-relaxed">{post.team_intro}</p>
          </Section>
        )}

        {/* Discord */}
        {post.discord && (
          <Section title="連絡先">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-[#5865F2]" />
              <span className="text-sm text-white">{post.discord}</span>
            </div>
          </Section>
        )}
      </div>
    </div>
  );
}
