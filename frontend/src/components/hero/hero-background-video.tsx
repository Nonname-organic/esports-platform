"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Hero のシネマティック背景。
 *
 * レイヤ構成（下 → 上）:
 *   1. アニメーション・グラデーション（動画が無くても"生きている"見た目を保証 / GPUのみ）
 *   2. <video>（WebM優先 → MP4フォールバック / poster / muted / loop / playsInline）
 *   3. Neon(Blue/Red)グロー + Dark/Gradientオーバーレイ（文字可読性のため 55〜70% 相当）
 *
 * 挙動:
 *   - prefers-reduced-motion: 動画を再生せず poster/グラデーションのみ。
 *   - IntersectionObserver: 画面外では pause（表示に戻れば再生）。
 *   - 動画未配置/失敗: onError で動画を隠し、下層のグラデーション/poster を見せる（CLS無し）。
 *
 * 動画URLは env で差し替え可能（CloudFront配信を想定）。未設定時は /hero/ 配下を参照。
 */

const WEBM = process.env.NEXT_PUBLIC_HERO_VIDEO_WEBM ?? "/hero/hero.webm";
const MP4 = process.env.NEXT_PUBLIC_HERO_VIDEO_MP4 ?? "/hero/hero.mp4";
const POSTER = process.env.NEXT_PUBLIC_HERO_POSTER ?? "/hero/hero-poster.svg";

export function HeroBackgroundVideo() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [ready, setReady] = useState(false); // 再生可能になったらフェードイン
  const [failed, setFailed] = useState(false);
  const [reduced, setReduced] = useState(false);

  // prefers-reduced-motion
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setReduced(mq.matches);
    apply();
    mq.addEventListener?.("change", apply);
    return () => mq.removeEventListener?.("change", apply);
  }, []);

  // IntersectionObserver: 画面外で pause / 画面内で play
  useEffect(() => {
    const el = videoRef.current;
    if (!el || reduced || failed) return;

    const io = new IntersectionObserver(
      (entries) => {
        const e = entries[0];
        if (!e) return;
        if (e.isIntersecting) {
          el.play().catch(() => {});
        } else {
          el.pause();
        }
      },
      { threshold: 0.1 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [reduced, failed]);

  const showVideo = !reduced && !failed;

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
      {/* 1. アニメーション・グラデーション（常時 / 動画の下） */}
      <div className="absolute inset-0 bg-slate-950" />
      <div className="absolute -inset-[15%] bg-[radial-gradient(50%_50%_at_28%_34%,rgba(37,99,235,0.45),transparent_60%)] animate-aurora will-change-transform" />
      <div className="absolute -inset-[15%] bg-[radial-gradient(48%_48%_at_76%_70%,rgba(225,29,72,0.38),transparent_60%)] animate-aurora-slow will-change-transform" />

      {/* 2. 動画 */}
      {showVideo && (
        <video
          ref={videoRef}
          className={`absolute inset-0 h-full w-full scale-105 object-cover transition-opacity duration-1000 ${
            ready ? "opacity-100" : "opacity-0"
          }`}
          style={{ filter: "brightness(0.55) contrast(1.06) saturate(1.05)" }}
          autoPlay
          muted
          loop
          playsInline
          preload="metadata"
          poster={POSTER}
          onCanPlay={() => setReady(true)}
          onError={() => setFailed(true)}
        >
          <source src={WEBM} type="video/webm" />
          <source src={MP4} type="video/mp4" />
        </video>
      )}

      {/* poster（reduced-motion / 動画非表示時に見せる静止画） */}
      {!showVideo && (
        <img
          src={POSTER}
          alt=""
          className="absolute inset-0 h-full w-full scale-105 object-cover opacity-90"
          style={{ filter: "brightness(0.6) contrast(1.05)" }}
        />
      )}

      {/* 3. オーバーレイ（Dark + Gradient + 微ブラー）: 文字可読性を担保 */}
      <div className="absolute inset-0 bg-slate-950/55" />
      <div className="absolute inset-0 bg-gradient-to-b from-slate-950/40 via-slate-950/45 to-slate-950" />
      <div className="absolute inset-0 bg-gradient-to-r from-slate-950/60 via-transparent to-slate-950/60" />
      {/* 下端を背景色へシームレスに接続 */}
      <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-b from-transparent to-slate-950" />
    </div>
  );
}
