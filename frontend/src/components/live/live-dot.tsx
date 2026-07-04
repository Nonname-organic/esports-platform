import { cn } from "@/lib/utils";

/** ゆっくり点滅する緑のLIVEドット（外側ping + 中央dot）。 */
export function LiveDot({ className }: { className?: string }) {
  return (
    <span className={cn("relative flex h-2.5 w-2.5", className)} aria-hidden>
      <span className="absolute inline-flex h-full w-full rounded-full bg-green-500 animate-live-ping" />
      <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-green-500 animate-live-blink" />
    </span>
  );
}

/** LIVE バッジ（ドット + テキスト）。緑・ゆっくり点滅。 */
export function LiveBadge({ label = "LIVE", className }: { label?: string; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-green-500/30 bg-green-500/10 px-2 py-0.5 text-[11px] font-bold tracking-wide text-green-400",
        className,
      )}
    >
      <LiveDot />
      {label}
    </span>
  );
}
