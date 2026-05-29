import Link from "next/link";
import { Trophy, Zap, Users, ChevronRight } from "lucide-react";
import { serverFetch } from "@/lib/api-client";
import { TournamentCard } from "@/features/tournaments/components/tournament-card";
import type { ListResponse, TournamentSummary } from "@/types/tournament";

// ISR: 5分ごとに再生成
export const revalidate = 300;

async function getFeaturedTournaments(): Promise<TournamentSummary[]> {
  try {
    const res = await serverFetch<ListResponse<TournamentSummary>>(
      "/api/v1/tournaments?status=ongoing&limit=3",
      undefined,
      { next: { revalidate: 300 } },
    );
    return res.data;
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const featured = await getFeaturedTournaments();

  return (
    <div className="mx-auto max-w-7xl px-4 py-16">
      {/* ヒーロー */}
      <section className="mb-20 text-center">
        <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-brand-500/30 bg-brand-500/10 px-4 py-1.5 text-sm font-semibold text-brand-400">
          <Zap className="h-3.5 w-3.5" />
          e-スポーツ大会管理プラットフォーム
        </div>
        <h1 className="mb-5 text-5xl font-black leading-tight text-white sm:text-6xl">
          大会運営を、
          <br />
          <span className="bg-gradient-to-r from-brand-400 to-cyan-400 bg-clip-text text-transparent">
            もっとシンプルに。
          </span>
        </h1>
        <p className="mb-8 text-lg text-slate-400 sm:text-xl max-w-2xl mx-auto">
          エントリー管理・ブラケット自動生成・リアルタイムスコア更新・
          <br className="hidden sm:block" />
          統計分析を一つのプラットフォームで完結。
        </p>
        <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
          <Link
            href="/tournaments"
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand-500 px-7 py-3.5 font-semibold text-white hover:bg-brand-600 transition-colors"
          >
            大会一覧を見る
            <ChevronRight className="h-4 w-4" />
          </Link>
          <Link
            href="/login"
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-7 py-3.5 font-semibold text-white hover:bg-white/10 transition-colors"
          >
            主催者としてログイン
          </Link>
        </div>
      </section>

      {/* 特徴 */}
      <section className="mb-20">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[
            {
              icon: Trophy,
              title: "ブラケット自動生成",
              desc: "シングルエリミネーション・ダブルエリミネーション・ラウンドロビンに対応。Bye処理も自動。",
              color: "text-yellow-400",
            },
            {
              icon: Zap,
              title: "リアルタイム更新",
              desc: "WebSocket でスコアをライブ反映。SQS による非同期イベント処理でランキングを自動更新。",
              color: "text-brand-400",
            },
            {
              icon: Users,
              title: "詳細な統計分析",
              desc: "マップ勝率・KDA・エージェント構成をチャートで可視化。大会単位・選手単位で集計。",
              color: "text-cyan-400",
            },
          ].map(({ icon: Icon, title, desc, color }) => (
            <div
              key={title}
              className="rounded-xl border border-white/10 bg-white/5 p-6 hover:bg-white/8 transition-colors"
            >
              <Icon className={`mb-3 h-8 w-8 ${color}`} />
              <h3 className="mb-2 font-bold text-white">{title}</h3>
              <p className="text-sm leading-relaxed text-slate-400">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 技術スタックバッジ */}
      <section className="mb-20">
        <p className="mb-4 text-center text-xs font-semibold uppercase tracking-widest text-slate-600">
          Technology Stack
        </p>
        <div className="flex flex-wrap justify-center gap-2">
          {[
            "Next.js 15",
            "FastAPI",
            "PostgreSQL",
            "Redis",
            "Docker",
            "AWS EC2",
            "SQS",
            "TanStack Query v5",
            "Recharts",
            "WebSocket",
          ].map((tech) => (
            <span
              key={tech}
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-slate-400"
            >
              {tech}
            </span>
          ))}
        </div>
      </section>

      {/* 開催中の大会 */}
      {featured.length > 0 && (
        <section>
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-xl font-bold text-white">開催中の大会</h2>
            <Link
              href="/tournaments?status=ongoing"
              className="flex items-center gap-1 text-sm text-brand-400 hover:text-brand-300"
            >
              すべて見る
              <ChevronRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {featured.map((t) => (
              <TournamentCard key={t.id} tournament={t} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
