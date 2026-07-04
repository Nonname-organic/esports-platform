"use client";

import Link from "next/link";
import { Trophy, Swords, ChevronDown } from "lucide-react";
import { useLive } from "@/features/live/provider/live-provider";
import { useRelativeSeconds } from "@/features/live/hooks/use-relative-seconds";
import { AnimatedNumber } from "@/components/live/animated-number";
import { LiveDot } from "@/components/live/live-dot";
import { HeroBackgroundVideo } from "./hero-background-video";

export function HeroSection() {
  const { live, lastUpdated } = useLive();
  const rel = useRelativeSeconds(lastUpdated);

  return (
    <section className="relative flex min-h-[calc(100svh-3.5rem)] w-full items-center justify-center overflow-hidden">
      <HeroBackgroundVideo />

      {/* コンテンツ */}
      <div className="relative z-10 mx-auto flex w-full max-w-4xl flex-col items-center px-4 py-20 text-center">
        {/* 上部: ライブ・ステータス（Hero内リアルタイム要素） */}
        <div className="mb-8 inline-flex flex-wrap items-center justify-center gap-x-4 gap-y-2 rounded-full border border-white/10 bg-white/[0.04] px-5 py-2 backdrop-blur-md">
          <span className="inline-flex items-center gap-2">
            <LiveDot />
            <span className="text-xs font-black tracking-widest text-green-400">LIVE</span>
          </span>
          <span className="hidden h-3.5 w-px bg-white/15 sm:block" />
          <LiveStat label="開催中" value={live?.ongoing_tournaments ?? 0} unit="大会" />
          <LiveStat label="進行中" value={live?.ongoing_matches ?? 0} unit="試合" />
          <LiveStat label="オンライン" value={live?.online_participants ?? 0} unit="人" />
          <span className="hidden text-[11px] text-slate-500 sm:inline">更新 {rel}</span>
        </div>

        {/* ブランド */}
        <h1 className="text-balance text-5xl font-black leading-[0.95] tracking-tight text-white drop-shadow-[0_2px_20px_rgba(0,0,0,0.6)] sm:text-7xl lg:text-8xl">
          <span className="bg-gradient-to-r from-brand-300 via-white to-red-300 bg-clip-text text-transparent">
            AXELIA
          </span>
          <span className="mt-2 block text-2xl font-bold tracking-[0.3em] text-slate-300 sm:text-3xl">
            TOURNAMENT PLATFORM
          </span>
        </h1>

        {/* サブコピー */}
        <p className="mt-6 text-lg font-medium tracking-wide text-slate-300 sm:text-2xl">
          開催する。<span className="text-brand-300">参加する。</span><span className="text-red-300">勝ち上がる。</span>
        </p>

        {/* CTA */}
        <div className="mt-10 flex flex-col gap-3 sm:flex-row">
          <Link
            href="/organizer/tournaments/new"
            className="group relative inline-flex items-center justify-center gap-2 rounded-xl bg-brand-500 px-8 py-4 text-base font-bold text-white shadow-[0_0_30px_rgba(59,130,246,0.45)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-brand-400 hover:shadow-[0_0_44px_rgba(59,130,246,0.75)]"
          >
            <Trophy className="h-5 w-5" />
            大会を開催する
            <span className="absolute inset-0 -z-10 rounded-xl bg-brand-500/40 blur-xl transition-opacity duration-200 group-hover:opacity-100 opacity-60" />
          </Link>
          <Link
            href="/tournaments"
            className="group inline-flex items-center justify-center gap-2 rounded-xl border border-white/20 bg-white/5 px-8 py-4 text-base font-bold text-white backdrop-blur-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-red-400/50 hover:bg-white/10 hover:shadow-[0_0_30px_rgba(225,29,72,0.35)]"
          >
            <Swords className="h-5 w-5 text-red-300" />
            大会へ参加する
          </Link>
        </div>
      </div>

      {/* スクロール誘導 */}
      <Link
        href="#live"
        aria-label="ライブ大会を見る"
        className="absolute bottom-6 left-1/2 z-10 flex -translate-x-1/2 flex-col items-center gap-2 text-slate-400 transition-colors hover:text-white animate-soft-float"
      >
        <span className="text-[11px] font-semibold uppercase tracking-[0.25em]">Explore Live Tournament</span>
        <span className="flex h-8 w-5 items-start justify-center rounded-full border-2 border-white/40 p-1">
          <span className="h-1.5 w-1 rounded-full bg-white/80 animate-scroll-wheel" />
        </span>
        <ChevronDown className="h-3.5 w-3.5" />
      </Link>
    </section>
  );
}

function LiveStat({ label, value, unit }: { label: string; value: number; unit: string }) {
  return (
    <span className="inline-flex items-baseline gap-1 text-xs text-slate-400">
      <span className="hidden text-slate-500 sm:inline">{label}</span>
      <span className="text-sm font-bold text-white">
        <AnimatedNumber value={value} durationMs={800} />
      </span>
      <span className="text-slate-500">{unit}</span>
    </span>
  );
}
