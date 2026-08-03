"use client";

import Link from "next/link";
import { Trophy, Swords, Users, Shield, Coins } from "lucide-react";
import { useLive } from "@/features/live/provider/live-provider";
import { useCountUp } from "@/features/live/hooks/use-count-up";
import { AnimatedNumber } from "@/components/live/animated-number";
import { HeroBackgroundVideo } from "./hero-background-video";
import { HeroArenaFx } from "./hero-arena-fx";
import { HeroCinematicOverlay } from "./hero-cinematic-overlay";
import { FloatingLiveCards } from "./floating-live-cards";
import { FeaturedEntry } from "./featured-entry";
import { usePointerParallax } from "./use-pointer-parallax";

/**
 * Hero Experience（Cinematic）。
 *
 * レイヤ（下 → 上）:
 *   Section → BackgroundVideo(Poster/Video/Grade) → ArenaFx → FloatingCards →
 *   CinematicOverlay(Dynamic Light/Vignette/Grain/Bottom Blend) → Content。
 *
 * Content は load 時に opacity/translateY で段階表示（.hero-reveal / stagger）。
 * マウス視差は usePointerParallax が section に CSS 変数を設定し、Dynamic Light が 1.5% 追従。
 * すべて GPU（transform・opacity・filter）。reduced-motion / Save-Data では静止・Poster のみ。
 */
export function HeroSection() {
  const sectionRef = usePointerParallax<HTMLElement>();

  return (
    <section
      ref={sectionRef}
      className="relative flex min-h-[calc(100svh-3.5rem)] w-full items-center justify-center overflow-hidden"
    >
      <HeroBackgroundVideo />
      <HeroArenaFx />
      <FloatingLiveCards />
      <HeroCinematicOverlay />

      {/* コンテンツ */}
      <div className="relative z-10 mx-auto flex w-full max-w-4xl flex-col items-center px-4 py-20 text-center">
        {/* Hero Copy（ブランド + インパクトコピー） */}
        <h1 className="hero-reveal text-balance text-6xl font-black leading-[0.95] tracking-tight text-white drop-shadow-[0_2px_28px_rgba(0,0,0,0.7)] sm:text-7xl lg:text-8xl">
          <span className="mb-5 block text-[11px] font-semibold tracking-[0.55em] text-slate-400 sm:text-xs">
            COMPETITIVE TOURNAMENT PLATFORM
          </span>
          <span className="bg-gradient-to-r from-brand-300 via-white to-red-300 bg-clip-text text-transparent">
            AXELIA
          </span>
          <span className="mt-4 block bg-gradient-to-b from-white to-slate-400/90 bg-clip-text text-2xl font-bold tracking-tight text-transparent sm:text-4xl lg:text-5xl">
            Every Tournament. One Platform.
          </span>
        </h1>

        {/* サブコピー */}
        <p className="hero-reveal hero-reveal-1 mt-6 text-lg font-medium tracking-wide text-slate-300 sm:text-2xl">
          開催する。<span className="text-brand-300">参加する。</span>
          <span className="text-red-300">勝ち上がる。</span>
        </p>

        {/* CTA */}
        <div className="hero-reveal hero-reveal-2 mt-10 flex flex-col gap-3 sm:flex-row">
          <Link
            href="/tournaments"
            className="arena-cta group relative inline-flex items-center justify-center gap-2 overflow-hidden rounded-xl bg-brand-500 px-8 py-4 text-base font-bold text-white shadow-[0_0_30px_rgba(59,130,246,0.45)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-brand-400 hover:shadow-[0_0_44px_rgba(59,130,246,0.75)] active:scale-[0.97]"
          >
            {/* Hover Light Sweep */}
            <span className="pointer-events-none absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/25 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
            <Swords className="relative h-5 w-5" />
            <span className="relative">大会を探す</span>
            <span className="absolute inset-0 -z-10 rounded-xl bg-brand-500/40 opacity-60 blur-xl transition-opacity duration-200 group-hover:opacity-100" />
          </Link>
          <Link
            href="/organizer/tournaments/new"
            className="arena-cta group relative inline-flex items-center justify-center gap-2 overflow-hidden rounded-xl bg-brand-500 px-8 py-4 text-base font-bold text-white shadow-[0_0_30px_rgba(59,130,246,0.45)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-brand-400 hover:shadow-[0_0_44px_rgba(59,130,246,0.75)] active:scale-[0.97]"
          >
            {/* Hover Light Sweep */}
            <span className="pointer-events-none absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/25 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
            <Trophy className="relative h-5 w-5" />
            <span className="relative">大会を掲載する</span>
            <span className="absolute inset-0 -z-10 rounded-xl bg-brand-500/40 opacity-60 blur-xl transition-opacity duration-200 group-hover:opacity-100" />
          </Link>
        </div>

        {/* Hero Statistics（実データ・静かな Fade・信頼感） */}
        <HeroStatistics className="hero-reveal hero-reveal-3" />

        {/* 受付中の目玉大会（締切が最も近い） */}
        <div className="hero-reveal hero-reveal-4 w-full">
          <FeaturedEntry />
        </div>
      </div>
    </section>
  );
}

/**
 * Hero Statistics — プラットフォーム累計（実データ / モックしない）。
 * アイコン + アクセント + ホバーグローの"魅せる"カード。
 * 取得後に 0 → 実値へ CountUp し、以降のポーリング更新でも増分をアニメーションで加算する。
 * 数値未取得の間は同じ高さで "—" を敷き、取得後に opacity だけで差し替える（CLS 0）。
 */
function HeroStatistics({ className = "" }: { className?: string }) {
  const { totals } = useLive();
  const items = [
    {
      icon: Trophy,
      label: "開催大会",
      value: totals?.tournaments ?? null,
      prize: false,
      chip: "bg-brand-500/15 text-brand-300",
      glow: "from-brand-500/30",
      hoverBorder: "hover:border-brand-400/40",
    },
    {
      icon: Users,
      label: "登録プレイヤー",
      value: totals?.players ?? null,
      prize: false,
      chip: "bg-emerald-500/15 text-emerald-300",
      glow: "from-emerald-500/30",
      hoverBorder: "hover:border-emerald-400/40",
    },
    {
      icon: Shield,
      label: "登録チーム",
      value: totals?.teams ?? null,
      prize: false,
      chip: "bg-violet-500/15 text-violet-300",
      glow: "from-violet-500/30",
      hoverBorder: "hover:border-violet-400/40",
    },
    {
      icon: Coins,
      label: "賞金総額",
      value: totals?.total_prize ?? null,
      prize: true,
      chip: "bg-amber-500/15 text-amber-300",
      glow: "from-amber-500/30",
      hoverBorder: "hover:border-amber-400/40",
    },
  ];

  return (
    <dl className={`mt-14 grid w-full max-w-3xl grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4 ${className}`}>
      {items.map(({ icon: Icon, label, value, prize, chip, glow, hoverBorder }) => (
        <div
          key={label}
          className={`group relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.035] px-4 py-5 text-center backdrop-blur-md transition-all duration-300 hover:-translate-y-1 ${hoverBorder}`}
        >
          {/* 上部グロー（ホバーで点灯） */}
          <div
            className={`pointer-events-none absolute -top-10 left-1/2 h-24 w-24 -translate-x-1/2 rounded-full bg-gradient-to-b ${glow} to-transparent opacity-0 blur-2xl transition-opacity duration-300 group-hover:opacity-100`}
          />
          <span className={`mx-auto mb-3 inline-flex h-9 w-9 items-center justify-center rounded-xl ${chip}`}>
            <Icon className="h-[18px] w-[18px]" />
          </span>
          <dd
            className="text-2xl font-black leading-none tracking-tight text-white transition-opacity duration-700 tabular-nums sm:text-3xl"
            style={{ opacity: value === null ? 0 : 1 }}
          >
            {value === null ? "—" : prize ? (
              <PrizeCountUp value={value} />
            ) : (
              <AnimatedNumber value={value} durationMs={1500} />
            )}
          </dd>
          <dt className="mt-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400 sm:text-[11px]">
            {label}
          </dt>
        </div>
      ))}
    </dl>
  );
}

/** 賞金総額のCountUp。生の金額を補間し、¥X万/億の表記でフォーマットして表示する。 */
function PrizeCountUp({ value }: { value: number }) {
  const n = useCountUp(value, 1500);
  return <span className="inline-block tabular-nums">{formatPrize(n)}</span>;
}

function formatPrize(n: number): string {
  if (n >= 100_000_000) return `¥${(n / 100_000_000).toFixed(1)}億`;
  if (n >= 10_000) return `¥${Math.round(n / 10_000).toLocaleString("ja-JP")}万`;
  return `¥${Math.round(n).toLocaleString("ja-JP")}`;
}
