"use client";

import { useState } from "react";
import { rankColor } from "@/lib/valorant";
import Link from "next/link";
import { Search, ChevronRight, Plus, Clock, MapPin } from "lucide-react";
import { useLFTList } from "@/features/lft/hooks/use-lft";
import { useAuthStore } from "@/store/auth-store";
import { cn } from "@/lib/utils";
import type { LFTPost } from "@/features/lft/api/lft-api";
import { ROLES, RANKS, REGIONS } from "./_components/lft-form";
import { ScoutFilterBar, type ScoutStatusOption } from "../_components/scout-filter-bar";


const STATUS_LABEL: Record<string, { label: string; cls: string }> = {
  open:        { label: "募集中",   cls: "bg-green-500/10 text-green-400" },
  negotiating: { label: "交渉中",   cls: "bg-yellow-500/10 text-yellow-400" },
  closed:      { label: "募集停止", cls: "bg-white/5 text-slate-500" },
};

const EXP_LABEL: Record<string, string> = {
  none: "大会未経験", some: "大会経験少", many: "大会経験多",
};

// フィルタピル配色はカードバッジ(STATUS_LABEL)と同系統
const FILTER_STATUSES: ScoutStatusOption[] = [
  { value: "", label: "すべて", activeCls: "bg-brand-500 text-white shadow-sm" },
  { value: "open", label: "募集中", dot: "bg-green-400", activeCls: "border-green-400/40 bg-green-500/20 text-green-300" },
  { value: "negotiating", label: "交渉中", dot: "bg-yellow-400", activeCls: "border-yellow-400/40 bg-yellow-500/20 text-yellow-300" },
  { value: "closed", label: "募集停止", dot: "bg-slate-400", activeCls: "border-slate-400/40 bg-slate-500/25 text-slate-200" },
];

export default function LFTListPage() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [filterRole, setFilterRole] = useState("");
  const [filterRegion, setFilterRegion] = useState("");
  const [filterRankMin, setFilterRankMin] = useState("");
  const [filterRankMax, setFilterRankMax] = useState("");
  const [filterStatus, setFilterStatus] = useState("open");

  const { data: posts, isLoading } = useLFTList({
    status: filterStatus || undefined,
    region: filterRegion || undefined,
    role: filterRole || undefined,
    min_rank: filterRankMin || undefined,
    max_rank: filterRankMax || undefined,
  });

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/scout" className="text-slate-500 hover:text-white transition-colors">Scout</Link>
          <ChevronRight className="h-4 w-4 text-slate-600" />
          <h1 className="text-xl font-black text-white">チームを探す (LFT)</h1>
        </div>
        {isAuthenticated && (
          <Link href="/scout/lft/me"
            className="flex items-center gap-2 rounded-xl bg-purple-500 px-4 py-2 text-sm font-bold text-white hover:bg-purple-600 transition-colors">
            <Plus className="h-4 w-4" /> 自分のLFT
          </Link>
        )}
      </div>

      <ScoutFilterBar
        statusOptions={FILTER_STATUSES}
        status={filterStatus}
        onStatus={setFilterStatus}
        role={filterRole}
        onRole={setFilterRole}
        roles={ROLES}
        rankMin={filterRankMin}
        onRankMin={setFilterRankMin}
        rankMax={filterRankMax}
        onRankMax={setFilterRankMax}
        ranks={RANKS}
        region={filterRegion}
        onRegion={setFilterRegion}
        regions={REGIONS}
      />

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-24 animate-pulse rounded-xl bg-white/5" />)}
        </div>
      ) : !posts || posts.length === 0 ? (
        <div className="flex flex-col items-center py-20 text-center">
          <Search className="mb-3 h-12 w-12 text-slate-700" />
          <p className="text-sm text-slate-500">条件に合うプレイヤーがいません</p>
          {isAuthenticated && (
            <Link href="/scout/lft/me" className="mt-4 rounded-xl bg-purple-500 px-5 py-2.5 text-sm font-bold text-white hover:bg-purple-600 transition-colors">
              LFTを登録する
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {posts.map((p) => <LFTCard key={p.id} post={p} />)}
        </div>
      )}
    </div>
  );
}

function LFTCard({ post }: { post: LFTPost }) {
  const st = STATUS_LABEL[post.status] ?? STATUS_LABEL.open;
  return (
    <Link href={`/scout/lft/${post.id}`}
      className="block rounded-xl border border-white/8 bg-slate-900 p-4 hover:border-purple-500/40 transition-colors">
      <div className="flex items-start gap-4">
        <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full border border-white/10 bg-slate-800 text-base font-bold text-slate-400">
          {post.avatar_url
            ? <img src={post.avatar_url} alt="" className="h-full w-full rounded-full object-cover" />
            : post.in_game_name.charAt(0)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 flex-wrap">
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-bold", st.cls)}>{st.label}</span>
                <span className="font-bold text-white">{post.in_game_name}</span>
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                {post.roles.map((r) => (
                  <span key={r} className="rounded-md bg-purple-500/10 px-2 py-0.5 text-[10px] font-semibold text-purple-400">{r}</span>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0 text-xs">
              {/* 大会実績（AXELIA競技ランキング — ランクマッチの自己申告より信頼できる実績） */}
              {post.tier_label && post.rp != null && post.rp > 0 && (
                <span
                  className="rounded-full border px-2 py-0.5 text-[10px] font-bold"
                  style={{ color: post.tier_color ?? undefined, borderColor: `${post.tier_color}66` }}
                  title={`大会実績: ${post.rp} RP${post.ranking ? ` / 総合${post.ranking}位` : ""}`}
                >
                  {post.tier_label} · {post.rp}RP
                </span>
              )}
              {(post.mvps ?? 0) > 0 && (
                <span className="text-[10px] font-bold text-yellow-400">⭐MVP×{post.mvps}</span>
              )}
              <span className={cn("font-bold", rankColor(post.current_rank))}>
                {post.current_rank}
              </span>
              {post.peak_rank !== post.current_rank && (
                <span className="text-slate-600">/ 最高 <span className={cn("font-semibold", rankColor(post.peak_rank))}>{post.peak_rank}</span></span>
              )}
            </div>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-[10px] text-slate-500">
            {post.region && <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{post.region}</span>}
            {post.activity_time.length > 0 && (
              <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{post.activity_time.slice(0, 2).join(" / ")}</span>
            )}
            {post.experience && <span>{EXP_LABEL[post.experience] ?? post.experience}</span>}
            {post.premier === "yes" && <span className="font-semibold text-yellow-500">Premier経験あり</span>}
            {post.agents.length > 0 && (
              <span>{post.agents.slice(0, 3).join(" / ")}{post.agents.length > 3 ? " ..." : ""}</span>
            )}
            {post.deadline && <span className="ml-auto text-slate-600">期限: {post.deadline}</span>}
          </div>
        </div>
      </div>
    </Link>
  );
}
