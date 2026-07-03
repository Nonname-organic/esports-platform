"use client";

import { useState } from "react";
import Link from "next/link";
import { Users, Filter, ChevronRight, Plus, Shield, Clock, MapPin, Star } from "lucide-react";
import { useLFPList } from "@/features/lfp/hooks/use-lfp";
import { useAuthStore } from "@/store/auth-store";
import { cn } from "@/lib/utils";
import type { LFPPost } from "@/features/lfp/api/lfp-api";

const ROLES = ["Duelist", "Initiator", "Controller", "Sentinel", "Flex", "IGL"];
const RANKS = ["Iron", "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Ascendant", "Immortal", "Radiant"];
const REGIONS = ["全国", "北海道", "東北", "関東", "中部", "関西", "中国", "四国", "九州", "海外", "オンラインのみ"];

const RANK_COLOR: Record<string, string> = {
  Iron: "text-slate-400", Bronze: "text-orange-700", Silver: "text-slate-300",
  Gold: "text-yellow-400", Platinum: "text-cyan-400", Diamond: "text-blue-400",
  Ascendant: "text-green-400", Immortal: "text-red-400", Radiant: "text-yellow-300",
};

const STATUS_LABEL: Record<string, { label: string; cls: string }> = {
  open: { label: "募集中", cls: "bg-green-500/10 text-green-400" },
  paused: { label: "一時停止", cls: "bg-yellow-500/10 text-yellow-400" },
  closed: { label: "募集終了", cls: "bg-white/5 text-slate-500" },
};

const sel = "rounded-lg border border-white/10 bg-slate-800 px-3 py-1.5 text-xs text-white outline-none focus:border-brand-500";

export default function LFPListPage() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [filterRole, setFilterRole] = useState("");
  const [filterRegion, setFilterRegion] = useState("");
  const [filterRank, setFilterRank] = useState("");
  const [filterStatus, setFilterStatus] = useState("open");

  const { data: posts, isLoading } = useLFPList({
    status: filterStatus || undefined,
    region: filterRegion || undefined,
    role: filterRole || undefined,
    min_rank: filterRank || undefined,
  });

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/scout" className="text-slate-500 hover:text-white transition-colors">Scout</Link>
          <ChevronRight className="h-4 w-4 text-slate-600" />
          <h1 className="text-xl font-black text-white">チーム募集 (LFP)</h1>
        </div>
        {isAuthenticated && (
          <Link href="/scout/lfp/new"
            className="flex items-center gap-2 rounded-xl bg-brand-500 px-4 py-2 text-sm font-bold text-white hover:bg-brand-600 transition-colors">
            <Plus className="h-4 w-4" /> 募集を作成
          </Link>
        )}
      </div>

      {/* フィルター */}
      <div className="mb-6 rounded-2xl border border-white/10 bg-slate-900 p-4 space-y-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
          <Filter className="h-3.5 w-3.5" />絞り込み
        </div>
        <div className="flex flex-wrap gap-3">
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className={sel}>
            <option value="">全ステータス</option>
            <option value="open">募集中</option>
            <option value="paused">一時停止</option>
            <option value="closed">募集終了</option>
          </select>
          <select value={filterRole} onChange={(e) => setFilterRole(e.target.value)} className={sel}>
            <option value="">全ロール</option>
            {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <select value={filterRank} onChange={(e) => setFilterRank(e.target.value)} className={sel}>
            <option value="">全ランク</option>
            {RANKS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <select value={filterRegion} onChange={(e) => setFilterRegion(e.target.value)} className={sel}>
            <option value="">全地域</option>
            {REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
      </div>

      {/* 結果 */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-28 animate-pulse rounded-xl bg-white/5" />
          ))}
        </div>
      ) : !posts || posts.length === 0 ? (
        <div className="flex flex-col items-center py-20 text-center">
          <Users className="mb-3 h-12 w-12 text-slate-700" />
          <p className="text-sm text-slate-500">条件に合う募集がありません</p>
          {isAuthenticated && (
            <Link href="/scout/lfp/new" className="mt-4 rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-bold text-white hover:bg-brand-600 transition-colors">
              最初の募集を作成
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {posts.map((p) => <LFPCard key={p.id} post={p} />)}
        </div>
      )}
    </div>
  );
}

function LFPCard({ post }: { post: LFPPost }) {
  const st = STATUS_LABEL[post.status] ?? STATUS_LABEL.open;
  return (
    <Link href={`/scout/lfp/${post.id}`}
      className="block rounded-xl border border-white/8 bg-slate-900 p-4 hover:border-brand-500/40 transition-colors">
      <div className="flex items-start gap-4">
        {/* チームロゴ */}
        <div className="h-12 w-12 flex-shrink-0 overflow-hidden rounded-xl border border-white/10 bg-slate-800 flex items-center justify-center">
          {post.team_logo_url
            ? <img src={post.team_logo_url} alt="" className="h-full w-full object-contain" />
            : <Shield className="h-6 w-6 text-slate-600" />}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 flex-wrap">
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-bold", st.cls)}>{st.label}</span>
                <span className="text-xs text-slate-500">{post.team_name} [{post.team_tag}]</span>
              </div>
              <h3 className="mt-0.5 text-sm font-bold text-white">{post.title}</h3>
            </div>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <span className={cn("text-xs font-bold", RANK_COLOR[post.min_rank] ?? "text-slate-400")}>
                {post.min_rank}〜
              </span>
              <span className="text-xs text-slate-500">· {post.headcount}名募集</span>
            </div>
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-2">
            {post.roles.map((r) => (
              <span key={r} className="rounded-md bg-brand-500/10 px-2 py-0.5 text-[10px] font-semibold text-brand-400">{r}</span>
            ))}
            {post.region && (
              <span className="flex items-center gap-1 text-[10px] text-slate-500">
                <MapPin className="h-3 w-3" />{post.region}
              </span>
            )}
            {post.activity_level && (
              <span className="flex items-center gap-1 text-[10px] text-slate-500">
                <Star className="h-3 w-3" />{post.activity_level}
              </span>
            )}
            {post.activity_time.length > 0 && (
              <span className="flex items-center gap-1 text-[10px] text-slate-500">
                <Clock className="h-3 w-3" />{post.activity_time.slice(0, 2).join(" / ")}
              </span>
            )}
            {post.deadline && (
              <span className="ml-auto text-[10px] text-slate-600">期限: {post.deadline}</span>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
