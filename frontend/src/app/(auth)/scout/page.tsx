"use client";

import Link from "next/link";
import { Users, Shield, ClipboardList, Search, ArrowRight } from "lucide-react";

const CARDS = [
  {
    href: "/scout/players",
    icon: Users,
    title: "Player Discovery",
    desc: "ゲーム・ロール・ランク・レーティングで選手を探す",
    color: "text-brand-400",
    bg: "bg-brand-500/10",
    border: "hover:border-brand-500/40",
  },
  {
    href: "/scout/teams",
    icon: Shield,
    title: "Team Discovery",
    desc: "募集中のチームをレーティング・地域で検索",
    color: "text-purple-400",
    bg: "bg-purple-500/10",
    border: "hover:border-purple-500/40",
  },
  {
    href: "/scout/recruitment",
    icon: ClipboardList,
    title: "Recruitment Board",
    desc: "チーム募集・選手募集の掲載と応募",
    color: "text-green-400",
    bg: "bg-green-500/10",
    border: "hover:border-green-500/40",
  },
];

export default function ScoutHomePage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <div className="mb-10 text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-500/10">
          <Search className="h-8 w-8 text-brand-400" />
        </div>
        <h1 className="text-3xl font-black text-white">Scout Platform</h1>
        <p className="mt-2 text-slate-400">チームと選手のマッチング基盤</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {CARDS.map((c) => (
          <Link
            key={c.href}
            href={c.href}
            className={`group rounded-2xl border border-white/10 bg-slate-900 p-6 transition-all ${c.border}`}
          >
            <div className={`mb-4 inline-flex rounded-xl p-3 ${c.bg}`}>
              <c.icon className={`h-6 w-6 ${c.color}`} />
            </div>
            <h2 className="text-lg font-bold text-white">{c.title}</h2>
            <p className="mt-1 text-sm text-slate-400">{c.desc}</p>
            <div className="mt-4 flex items-center gap-1 text-sm font-semibold text-brand-400 opacity-0 transition-opacity group-hover:opacity-100">
              開く <ArrowRight className="h-4 w-4" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
