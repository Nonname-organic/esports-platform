"use client";

import { useState } from "react";
import { Play, ExternalLink, Radio } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTournamentOverview } from "@/features/tournament-live/hooks/use-tournament-live";
import { LiveDot } from "@/components/live/live-dot";

/** 埋め込みURLを算出（不可なら null → 外部リンク）。 */
function embedUrl(url: string, platform: string): string | null {
  try {
    if (platform === "youtube") {
      const m = url.match(/(?:v=|youtu\.be\/|\/live\/|\/embed\/)([\w-]{11})/);
      return m ? `https://www.youtube.com/embed/${m[1]}?autoplay=1` : null;
    }
    if (platform === "twitch") {
      const ch = url.match(/twitch\.tv\/([\w]+)/)?.[1];
      const parent = typeof window !== "undefined" ? window.location.hostname : "localhost";
      return ch ? `https://player.twitch.tv/?channel=${ch}&parent=${parent}&autoplay=true` : null;
    }
    if (platform === "kick") {
      const ch = url.match(/kick\.com\/([\w-]+)/)?.[1];
      return ch ? `https://player.kick.com/${ch}` : null;
    }
  } catch { /* ignore */ }
  return null;
}

/** TournamentStreamCard: 公式配信の埋め込み（Lazy / click-to-load / SSR Safe）。 */
export function StreamCard({ tournamentId }: { tournamentId: string }) {
  const { data } = useTournamentOverview(tournamentId);
  const [loaded, setLoaded] = useState(false);
  const stream = data?.stream;
  if (!stream) return null;

  const embed = embedUrl(stream.url, stream.platform);

  return (
    <section className="overflow-hidden rounded-2xl border border-white/10 bg-slate-900">
      <div className="flex items-center gap-2 border-b border-white/8 px-4 py-2.5">
        <Radio className="h-4 w-4 text-red-400" />
        <span className="text-sm font-bold text-white">配信</span>
        <span className="text-[11px] uppercase tracking-wider text-slate-500">{stream.platform}</span>
        {stream.is_live && (
          <span className="ml-auto inline-flex items-center gap-1.5 text-[11px] font-black text-red-400">
            <LiveDot /> LIVE
          </span>
        )}
      </div>

      <div className="relative aspect-video bg-slate-950">
        {loaded && embed ? (
          <iframe
            src={embed}
            title="Tournament stream"
            className="absolute inset-0 h-full w-full"
            allow="autoplay; fullscreen; encrypted-media"
            allowFullScreen
            loading="lazy"
          />
        ) : (
          <button
            onClick={() => { if (embed) setLoaded(true); else window.open(stream.url, "_blank", "noopener"); }}
            className="group absolute inset-0 flex flex-col items-center justify-center gap-3 bg-[radial-gradient(ellipse_at_center,rgba(239,68,68,0.15),transparent_70%)]"
          >
            <span className={cn(
              "flex h-16 w-16 items-center justify-center rounded-full border-2 border-white/30 bg-black/40 backdrop-blur-sm transition-transform group-hover:scale-110",
              stream.is_live && "animate-glow-pulse",
            )}>
              {embed ? <Play className="ml-1 h-7 w-7 text-white" /> : <ExternalLink className="h-6 w-6 text-white" />}
            </span>
            <span className="text-xs font-bold text-slate-300">
              {embed ? "クリックして配信を再生" : "配信を開く"}
            </span>
          </button>
        )}
      </div>
    </section>
  );
}
