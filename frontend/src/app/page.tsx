import { Trophy, Zap, Users } from "lucide-react";
import { serverFetch } from "@/lib/api-client";
import { LandingLive } from "@/components/live/landing-live";
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

const FEATURES = [
  {
    icon: Trophy,
    title: "ブラケット自動生成",
    desc: "シングル/ダブルエリミ・ラウンドロビンに対応。Bye処理も自動。",
    color: "text-yellow-400",
  },
  {
    icon: Zap,
    title: "リアルタイム更新",
    desc: "スコア・ランキングをライブ反映。大会の熱が止まらない。",
    color: "text-brand-400",
  },
  {
    icon: Users,
    title: "詳細な統計分析",
    desc: "マップ勝率・KDA・構成をチャートで可視化。選手/大会単位で集計。",
    color: "text-cyan-400",
  },
];

export default async function HomePage() {
  const featured = await getFeaturedTournaments();

  return (
    <>
      {/* Hero（背景動画）＋ ライブ体験（Status Bar / Statistics / Preview / Activity） */}
      <LandingLive initialFeatured={featured} />

      {/* 機能ハイライト（その他説明・控えめ） */}
      <section className="mx-auto max-w-7xl px-4 pb-20">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, desc, color }) => (
            <div
              key={title}
              className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 transition-colors hover:bg-white/[0.06]"
            >
              <Icon className={`mb-3 h-7 w-7 ${color}`} />
              <h3 className="mb-2 font-bold text-white">{title}</h3>
              <p className="text-sm leading-relaxed text-slate-400">{desc}</p>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
