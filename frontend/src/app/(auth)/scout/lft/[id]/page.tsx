"use client";

import { use } from "react";
import { rankColor } from "@/lib/valorant";
import Link from "next/link";
import { ChevronRight, MapPin, Clock, Trophy, Calendar, MessageSquare, Twitter, Edit2, User2 } from "lucide-react";
import { useLFT } from "@/features/lft/hooks/use-lft";
import { useAuthStore } from "@/store/auth-store";
import { cn } from "@/lib/utils";


const STATUS_LABEL: Record<string, { label: string; cls: string }> = {
  open:        { label: "募集中",   cls: "bg-green-500/10 text-green-400 border-green-500/20" },
  negotiating: { label: "交渉中",   cls: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20" },
  closed:      { label: "募集停止", cls: "bg-white/5 text-slate-500 border-white/10" },
};

const EXP_LABEL: Record<string, string> = { none: "なし", some: "少しあり", many: "多数あり" };
const PREMIER_LABEL: Record<string, string> = { none: "なし", yes: "あり" };

export default function LFTDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: post, isLoading } = useLFT(id);
  const user = useAuthStore((s) => s.user);

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
        <p className="text-slate-400">LFTが見つかりません</p>
        <Link href="/scout/lft" className="mt-4 text-brand-400 hover:underline">一覧に戻る</Link>
      </div>
    );
  }

  const st = STATUS_LABEL[post.status] ?? STATUS_LABEL.open;
  const isOwner = user?.id === post.user_id;

  const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <div className="rounded-2xl border border-white/10 bg-slate-900 p-5">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">{title}</h2>
      {children}
    </div>
  );

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6 flex items-center gap-2 text-sm text-slate-400">
        <Link href="/scout" className="hover:text-white">Scout</Link>
        <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
        <Link href="/scout/lft" className="hover:text-white">LFT</Link>
        <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
        <span className="truncate text-white">{post.in_game_name}</span>
      </div>

      {/* ヘッダー */}
      <div className="mb-5 rounded-2xl border border-white/10 bg-slate-900 p-5">
        <div className="flex items-start gap-4">
          <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-full border border-white/10 bg-slate-800 text-lg font-bold text-slate-400">
            {post.avatar_url
              ? <img src={post.avatar_url} alt="" className="h-full w-full rounded-full object-cover" />
              : post.in_game_name.charAt(0)}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={cn("rounded-full border px-2.5 py-0.5 text-xs font-bold", st.cls)}>{st.label}</span>
            </div>
            <h1 className="mt-1 text-xl font-black text-white">{post.in_game_name}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                現在 <span className={cn("font-bold", rankColor(post.current_rank))}>{post.current_rank}</span>
              </span>
              <span className="flex items-center gap-1">
                最高 <span className={cn("font-bold", rankColor(post.peak_rank))}>{post.peak_rank}</span>
              </span>
              {post.region && <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{post.region}</span>}
              {post.deadline && <span className="flex items-center gap-1"><Calendar className="h-3 w-3" />期限 {post.deadline}</span>}
            </div>
          </div>
          <div className="flex flex-shrink-0 flex-col items-end gap-2">
            {/* 主要導線: プレイヤープロフィールへ（見落とし防止のためボタン化） */}
            <Link href={`/players/${post.player_id}`}
              className="flex items-center gap-1.5 rounded-lg bg-brand-500 px-3.5 py-2 text-xs font-bold text-white hover:bg-brand-600 transition-colors">
              <User2 className="h-3.5 w-3.5" /> プロフィールを見る
            </Link>
            {isOwner && (
              <Link href="/scout/lft/me"
                className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:text-white transition-colors">
                <Edit2 className="h-3.5 w-3.5" /> 編集
              </Link>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <Section title="希望ロール">
          <div className="flex flex-wrap gap-2">
            {post.roles.map((r) => (
              <span key={r} className="rounded-lg bg-purple-500/10 px-3 py-1.5 text-sm font-semibold text-purple-400">{r}</span>
            ))}
          </div>
        </Section>

        {post.agents.length > 0 && (
          <Section title="メインエージェント">
            <div className="flex flex-wrap gap-2">
              {post.agents.map((a) => (
                <span key={a} className="rounded-lg bg-white/5 px-3 py-1.5 text-sm text-slate-300">{a}</span>
              ))}
            </div>
          </Section>
        )}

        <Section title="活動情報">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            {post.activity_time.length > 0 && (
              <div>
                <p className="mb-1 flex items-center gap-1 text-xs text-slate-500"><Clock className="h-3 w-3" />活動時間</p>
                <p className="text-sm text-white">{post.activity_time.join(" / ")}</p>
              </div>
            )}
            {post.experience && (
              <div>
                <p className="mb-1 flex items-center gap-1 text-xs text-slate-500"><Trophy className="h-3 w-3" />大会経験</p>
                <p className="text-sm text-white">{EXP_LABEL[post.experience] ?? post.experience}</p>
              </div>
            )}
            {post.premier && (
              <div>
                <p className="mb-1 text-xs text-slate-500">Premier経験</p>
                <p className="text-sm text-white">{PREMIER_LABEL[post.premier] ?? post.premier}</p>
              </div>
            )}
          </div>
        </Section>

        {post.description && (
          <Section title="自己PR">
            <p className="whitespace-pre-wrap text-sm text-slate-300 leading-relaxed">{post.description}</p>
          </Section>
        )}

        {post.conditions && (
          <Section title="希望条件">
            <p className="whitespace-pre-wrap text-sm text-slate-300 leading-relaxed">{post.conditions}</p>
          </Section>
        )}

        {(post.discord || post.twitter) && (
          <Section title="連絡先">
            <div className="flex flex-wrap gap-4">
              {post.discord && (
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-[#5865F2]" />
                  <span className="text-sm text-white">{post.discord}</span>
                </div>
              )}
              {post.twitter && (
                <a href={`https://twitter.com/${post.twitter.replace(/^@/, "")}`} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-white hover:text-brand-400 transition-colors">
                  <Twitter className="h-4 w-4 text-sky-400" />
                  {post.twitter}
                </a>
              )}
            </div>
          </Section>
        )}
      </div>
    </div>
  );
}
