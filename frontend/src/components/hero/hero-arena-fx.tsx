/**
 * Hero を「大会会場」に見せる CSS のみの環境演出（Canvas不要 / GPU）。
 *  - ステージライト風の移動グロー（Light Sweep ×2）
 *  - 大型スクリーンのスキャンライン質感（極薄）
 *  - 画面下部の観客シルエット
 * すべて pointer-events:none。reduced-motion では停止（アニメのみ、形状は残る）。
 */
export function HeroArenaFx() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
      {/* ステージライトの移動グロー */}
      <div className="absolute -top-1/3 left-0 h-[140%] w-40 rotate-[9deg] bg-[linear-gradient(90deg,transparent,rgba(147,197,253,0.10),transparent)] blur-2xl animate-light-sweep" />
      <div className="absolute -top-1/3 left-0 h-[140%] w-56 rotate-[9deg] bg-[linear-gradient(90deg,transparent,rgba(216,180,254,0.09),transparent)] blur-2xl animate-light-sweep-2" />

      {/* 大型スクリーン風スキャンライン（極薄・静止） */}
      <div
        className="absolute inset-0 opacity-[0.05]"
        style={{ backgroundImage: "repeating-linear-gradient(0deg, rgba(255,255,255,0.6) 0px, rgba(255,255,255,0.6) 1px, transparent 1px, transparent 3px)" }}
      />

      {/* 観客席のシルエット（下部） */}
      <div className="absolute inset-x-0 bottom-0 h-24 opacity-70">
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950 to-transparent" />
        <svg className="absolute bottom-0 h-16 w-full" preserveAspectRatio="none" viewBox="0 0 1200 80" fill="rgb(2 6 23)">
          <path d="M0 80 V50 Q30 40 60 48 T120 46 T180 50 T240 44 T300 50 T360 46 T420 52 T480 45 T540 50 T600 44 T660 50 T720 46 T780 52 T840 45 T900 50 T960 44 T1020 50 T1080 47 T1140 51 T1200 46 V80 Z" />
        </svg>
        {/* 観客のペンライト風の点（静止・微発光） */}
        <div className="absolute bottom-6 left-0 h-1 w-full opacity-60"
          style={{ backgroundImage: "radial-gradient(circle, rgba(96,165,250,0.8) 1px, transparent 1.5px)", backgroundSize: "34px 8px" }} />
      </div>
    </div>
  );
}
