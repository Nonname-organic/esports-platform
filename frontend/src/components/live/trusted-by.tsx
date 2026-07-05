import { cn } from "@/lib/utils";

/**
 * 社会的証明のロゴ/チーム名マーキー（静的・SSR / SEOフレンドリー）。
 * 既定はグレー、hover で発色。CSS マーキー（transform のみ / reduced-motion で静止）。
 */
const TEAMS = ["VARREL", "REJECT", "ZETA", "FENNEL", "RIDDLE", "SCARZ", "NORTHEPTION", "CGA"];

export function TrustedBy() {
  const row = [...TEAMS, ...TEAMS]; // シームレスループ用に2周分

  return (
    <section className="mx-auto max-w-7xl px-4 pb-20">
      <p className="mb-6 text-center text-[11px] font-bold uppercase tracking-[0.3em] text-slate-600">
        Trusted by Teams
      </p>
      <div className="group relative overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_12%,black_88%,transparent)]">
        <div className="flex w-max animate-marquee items-center gap-12 group-hover:[animation-play-state:paused]">
          {row.map((name, i) => (
            <span
              key={`${name}-${i}`}
              className={cn(
                "select-none whitespace-nowrap text-2xl font-black tracking-wider text-slate-700 transition-colors duration-300",
                "hover:text-white sm:text-3xl",
              )}
            >
              {name}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
