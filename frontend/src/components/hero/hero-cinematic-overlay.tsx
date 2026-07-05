/**
 * Hero の最上位シネマティック層（背景と Content の間）。
 *
 * レイヤ（下 → 上）:
 *   1. Dynamic Light … 巨大 radial を 50s ドリフト（hero-light-drift）+ マウス 1.5% 追従。
 *                       画面全体に "呼吸" を与える（見えるか見えないか程度）。
 *   2. Soft Vignette  … 周辺を少し暗くして文字を自然に浮かせる（強すぎない）。
 *   3. Film Grain     … 極薄の静止ノイズ（hero-grain）で高級感を出す。
 *   4. Bottom Blend   … 次セクションへ境界を感じさせず溶け込ませる。
 *
 * すべて pointer-events:none / aria-hidden。GPU（transform・opacity）のみ。
 * マウス追従は親 <section> が持つ CSS 変数 --hero-mx/--hero-my を継承して使う
 * （usePointerParallax が設定。無ければ 0 = 無効でも破綻しない）。
 * reduced-motion 時は hero-light-drift が停止（globals.css）、grain は静止のまま。
 */
export function HeroCinematicOverlay() {
  return (
    <div className="pointer-events-none absolute inset-0 z-[1] overflow-hidden" aria-hidden>
      {/* 1. Dynamic Light（マウスで 1.5% だけ追従 → ease で滑らかに） */}
      <div
        className="absolute inset-0"
        style={{
          transform:
            "translate3d(calc(var(--hero-mx, 0) * 1.5%), calc(var(--hero-my, 0) * 1.5%), 0)",
          transition: "transform 0.5s cubic-bezier(0.22, 1, 0.36, 1)",
        }}
      >
        <div className="hero-light-drift absolute -inset-[25%] bg-[radial-gradient(40%_40%_at_50%_42%,rgba(59,130,246,0.18),rgba(147,51,234,0.07)_50%,transparent_72%)]" />
      </div>

      {/* 2. Soft Vignette（周辺減光） */}
      <div className="absolute inset-0 bg-[radial-gradient(120%_120%_at_50%_45%,transparent_55%,rgba(2,6,23,0.55)_100%)]" />

      {/* 3. Film Grain（静止・極薄） */}
      <div className="hero-grain absolute inset-0" />

      {/* 4. Bottom Blend（次セクションへ溶かす） */}
      <div className="absolute inset-x-0 bottom-0 h-56 bg-gradient-to-b from-transparent to-slate-950" />
    </div>
  );
}
