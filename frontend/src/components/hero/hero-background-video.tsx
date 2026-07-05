"use client";

import { useEffect, useMemo, useRef, useState } from "react";

/**
 * Hero のシネマティック背景。
 *
 * レイヤ構成（下 → 上）:
 *   1. アニメーション・グラデーション（動画が無くても"生きている"見た目 / GPUのみ・Blue/Purple/Red Neon）
 *   2. <video>（WebM優先 → MP4 / poster / muted / loop / playsInline / Desktop・Mobile分離）
 *   3. 強めの Dark + Gradient オーバーレイ（UIが必ず前面に見えるよう不透明度高め）
 *
 * 挙動:
 *   - prefers-reduced-motion: 動画を再生せず poster/グラデーションのみ。
 *   - IntersectionObserver: 画面外では pause。
 *   - 動画未配置/失敗: onError で動画を隠し、下層グラデーション/poster を表示（CLS無し）。
 *
 * 動画URLは env で差し替え可能（CloudFront配信想定）。Mobile用は軽量版を別指定可能。
 * 素材側で 5〜8秒ごとのカット/クロスフェード・HUD/文字/実況なしのシネマティックPVを推奨。
 */

const D_WEBM = process.env.NEXT_PUBLIC_HERO_VIDEO_WEBM ?? "/hero/hero.webm";
const D_MP4 = process.env.NEXT_PUBLIC_HERO_VIDEO_MP4 ?? "/hero/hero.mp4";
const T_WEBM = process.env.NEXT_PUBLIC_HERO_VIDEO_WEBM_TABLET ?? D_WEBM;
const T_MP4 = process.env.NEXT_PUBLIC_HERO_VIDEO_MP4_TABLET ?? D_MP4;
const M_WEBM = process.env.NEXT_PUBLIC_HERO_VIDEO_WEBM_MOBILE ?? T_WEBM;
const M_MP4 = process.env.NEXT_PUBLIC_HERO_VIDEO_MP4_MOBILE ?? T_MP4;
const POSTER = process.env.NEXT_PUBLIC_HERO_POSTER ?? "/hero/hero-poster.svg";

type Tier = "desktop" | "tablet" | "mobile";
function pickTier(): Tier {
  if (typeof window === "undefined") return "desktop";
  if (window.matchMedia("(max-width: 640px)").matches) return "mobile";
  if (window.matchMedia("(max-width: 1024px)").matches) return "tablet";
  return "desktop";
}
const TIER_SOURCES: Record<Tier, { webm: string; mp4: string }> = {
  desktop: { webm: D_WEBM, mp4: D_MP4 },
  tablet: { webm: T_WEBM, mp4: T_MP4 },
  mobile: { webm: M_WEBM, mp4: M_MP4 },
};

export function HeroBackgroundVideo() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [reduced, setReduced] = useState(false);
  const [tier, setTier] = useState<Tier>("desktop");

  // prefers-reduced-motion
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setReduced(mq.matches);
    apply();
    mq.addEventListener?.("change", apply);
    return () => mq.removeEventListener?.("change", apply);
  }, []);

  // ビューポートに応じた別動画（Desktop / Tablet / Mobile）
  useEffect(() => {
    const apply = () => setTier(pickTier());
    apply();
    const mqs = [window.matchMedia("(max-width: 640px)"), window.matchMedia("(max-width: 1024px)")];
    mqs.forEach((mq) => mq.addEventListener?.("change", apply));
    return () => mqs.forEach((mq) => mq.removeEventListener?.("change", apply));
  }, []);

  const sources = useMemo(() => TIER_SOURCES[tier], [tier]);

  // ソース切替時に再読込
  useEffect(() => {
    if (videoRef.current && !reduced && !failed) {
      setReady(false);
      videoRef.current.load();
    }
  }, [sources, reduced, failed]);

  // IntersectionObserver: 画面外で pause / 画面内で play
  useEffect(() => {
    const el = videoRef.current;
    if (!el || reduced || failed) return;
    const io = new IntersectionObserver(
      (entries) => {
        const e = entries[0];
        if (!e) return;
        if (e.isIntersecting) el.play().catch(() => {});
        else el.pause();
      },
      { threshold: 0.1 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [reduced, failed]);

  const showVideo = !reduced && !failed;

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
      {/* 1. アニメーション・グラデーション（Blue / Purple / Red Neon） */}
      <div className="absolute inset-0 bg-slate-950" />
      <div className="absolute -inset-[15%] bg-[radial-gradient(50%_50%_at_26%_32%,rgba(37,99,235,0.5),transparent_60%)] animate-aurora will-change-transform" />
      <div className="absolute -inset-[15%] bg-[radial-gradient(46%_46%_at_50%_60%,rgba(147,51,234,0.4),transparent_60%)] animate-aurora-slow will-change-transform" />
      <div className="absolute -inset-[15%] bg-[radial-gradient(48%_48%_at_78%_70%,rgba(225,29,72,0.42),transparent_60%)] animate-aurora will-change-transform" />

      {/* 2. 動画 */}
      {showVideo && (
        <video
          ref={videoRef}
          key={tier}
          className={`absolute inset-0 h-full w-full scale-105 object-cover transition-opacity duration-1000 ${
            ready ? "opacity-100" : "opacity-0"
          }`}
          style={{ filter: "brightness(0.5) contrast(1.08) saturate(1.08)" }}
          autoPlay
          muted
          loop
          playsInline
          preload="metadata"
          poster={POSTER}
          onCanPlay={() => setReady(true)}
          onError={() => setFailed(true)}
        >
          <source src={sources.webm} type="video/webm" />
          <source src={sources.mp4} type="video/mp4" />
        </video>
      )}

      {/* poster（reduced-motion / 動画非表示時） */}
      {!showVideo && (
        <img
          src={POSTER}
          alt=""
          className="absolute inset-0 h-full w-full scale-105 object-cover opacity-90"
          style={{ filter: "brightness(0.55) contrast(1.05)" }}
        />
      )}

      {/* 3. オーバーレイ（強め: UIを必ず前面に） */}
      <div className="absolute inset-0 bg-slate-950/65" />
      <div className="absolute inset-0 bg-gradient-to-b from-slate-950/55 via-slate-950/45 to-slate-950" />
      <div className="absolute inset-0 bg-gradient-to-r from-slate-950/70 via-transparent to-slate-950/70" />
      <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-b from-transparent to-slate-950" />
    </div>
  );
}
