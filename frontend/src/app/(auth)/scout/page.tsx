"use client";

import Link from "next/link";
import { Search, UserSearch, UserPlus, ArrowRight } from "lucide-react";

/**
 * Scout ハブ — 目的が一目で分かる 2 択のみ。
 *   選手募集 (LFT) … チームを探している選手の掲示板  → /scout/lft
 *   チーム募集 (LFP) … メンバーを募集しているチームの掲示板 → /scout/lfp
 * ※ Player/Team Discovery・Recruitment Board はページとしては残す（URL直アクセス可）が、
 *   直感性を優先しハブからは外す。
 */
const CARDS = [
  {
    href: "/scout/lft",
    icon: UserSearch,
    tag: "LFT · Looking For Team",
    title: "選手募集",
    desc: "チームを探している選手を見つける掲示板。",
    points: ["選手を探す・スカウトする", "選手として自分を掲載する"],
    color: "text-pink-300",
    bg: "bg-pink-500/10",
    ring: "hover:border-pink-400/50 hover:shadow-[0_0_55px_-18px_rgba(236,72,153,0.75)]",
    dot: "bg-pink-400",
  },
  {
    href: "/scout/lfp",
    icon: UserPlus,
    tag: "LFP · Looking For Players",
    title: "チーム募集",
    desc: "メンバーを募集しているチームを見つける掲示板。",
    points: ["チームを探す・応募する", "チームの募集を掲載する"],
    color: "text-emerald-300",
    bg: "bg-emerald-500/10",
    ring: "hover:border-emerald-400/50 hover:shadow-[0_0_55px_-18px_rgba(16,185,129,0.75)]",
    dot: "bg-emerald-400",
  },
];

export default function ScoutHomePage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <div className="mb-10 text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-500/10">
          <Search className="h-8 w-8 text-brand-400" />
        </div>
        <h1 className="text-3xl font-black text-white">スカウト</h1>
        <p className="mt-2 text-slate-400">選手とチームのマッチング。目的に合わせて選んでください。</p>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        {CARDS.map((c) => (
          <Link
            key={c.href}
            href={c.href}
            className={`group relative flex flex-col overflow-hidden rounded-2xl border border-white/10 bg-slate-900 p-7 transition-all duration-300 hover:-translate-y-1 ${c.ring}`}
          >
            <div className="flex items-center justify-between">
              <div className={`inline-flex rounded-2xl p-3.5 ${c.bg}`}>
                <c.icon className={`h-7 w-7 ${c.color}`} />
              </div>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 px-3 py-1 text-[10px] font-bold tracking-wider text-slate-400">
                <span className={`h-1.5 w-1.5 rounded-full ${c.dot}`} /> {c.tag}
              </span>
            </div>

            <h2 className="mt-5 text-2xl font-black text-white">{c.title}</h2>
            <p className="mt-1.5 text-sm text-slate-400">{c.desc}</p>

            <ul className="mt-5 space-y-2">
              {c.points.map((p) => (
                <li key={p} className="flex items-center gap-2 text-sm text-slate-300">
                  <span className={`h-1 w-1 rounded-full ${c.dot}`} />
                  {p}
                </li>
              ))}
            </ul>

            <div className={`mt-6 inline-flex items-center gap-1 text-sm font-bold ${c.color}`}>
              開く <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
