"use client";

import { useEffect, useRef, useState } from "react";
import { Sparkles, ShieldCheck, AlertTriangle, Target, Zap, UserCog, Swords } from "lucide-react";
import { cn } from "@/lib/utils";
import { usePlayerAnalysis } from "@/features/player-profile/hooks/use-player-profile";

/** テキストを1文字ずつ表示（reduced-motion では即全文）。 */
function useTypewriter(text: string, speed = 18): string {
  const [out, setOut] = useState("");
  const ref = useRef(text);
  useEffect(() => {
    ref.current = text;
    if (typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      setOut(text);
      return;
    }
    setOut("");
    let i = 0;
    const id = setInterval(() => {
      i += 1;
      setOut(text.slice(0, i));
      if (i >= text.length) clearInterval(id);
    }, speed);
    return () => clearInterval(id);
  }, [text, speed]);
  return out;
}

export function AiAnalysisCard({ playerId }: { playerId: string }) {
  const { data, isLoading } = usePlayerAnalysis(playerId);
  const typed = useTypewriter(data?.summary ?? "");

  if (isLoading) {
    return (
      <section className="rounded-2xl border border-purple-500/20 bg-slate-900 p-5">
        <div className="mb-4 h-4 w-32 animate-pulse rounded bg-white/10" />
        <div className="space-y-2">
          <div className="h-3 w-full animate-pulse rounded bg-white/5" />
          <div className="h-3 w-4/5 animate-pulse rounded bg-white/5" />
        </div>
      </section>
    );
  }
  if (!data) return null;

  return (
    <section className="relative overflow-hidden rounded-2xl border border-purple-500/25 bg-gradient-to-br from-slate-900 to-slate-950 p-5">
      <div className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-purple-500/10 blur-3xl" />
      <div className="relative">
        <div className="mb-3 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-purple-400" />
          <h2 className="font-bold text-white">AI ANALYSIS</h2>
          <span className="rounded-full border border-purple-500/30 bg-purple-500/10 px-2 py-0.5 text-[10px] font-bold text-purple-300">
            {data.provider === "rule_based" ? "Rule-based · LLM-ready" : data.provider}
          </span>
          <span className="ml-auto rounded-md bg-white/5 px-2 py-0.5 text-[11px] font-black text-white">{data.play_style}</span>
        </div>

        {/* サマリ（Typewriter） */}
        <p className="min-h-[2.5rem] text-sm leading-relaxed text-slate-300">
          {typed}
          {typed.length < (data.summary?.length ?? 0) && <span className="ml-0.5 inline-block h-3.5 w-0.5 animate-live-blink bg-purple-400 align-middle" />}
        </p>

        {/* Consistency / Aggression */}
        <div className="mt-4 grid grid-cols-2 gap-4">
          <Meter icon={Target} label="Consistency" value={data.consistency} color="#22d3ee" />
          <Meter icon={Zap} label="Aggression" value={data.aggression} color="#f43f5e" />
        </div>

        {/* Strengths / Weaknesses */}
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <List icon={ShieldCheck} color="text-green-400" title="強み" items={data.strengths} />
          <List icon={AlertTriangle} color="text-amber-400" title="課題" items={data.weaknesses} />
        </div>

        {/* Recommended */}
        <div className="mt-4 flex flex-wrap gap-2 border-t border-white/8 pt-4">
          {data.recommended_role && (
            <Chip icon={UserCog} color="text-brand-400">推奨ロール <b className="text-white">{data.recommended_role}</b></Chip>
          )}
          {data.recommended_agent && (
            <Chip icon={Swords} color="text-red-400">推奨エージェント <b className="text-white">{data.recommended_agent}</b></Chip>
          )}
        </div>
      </div>
    </section>
  );
}

function Meter({ icon: Icon, label, value, color }: { icon: React.ElementType; label: string; value: number; color: string }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-[11px]">
        <span className="inline-flex items-center gap-1 text-slate-400"><Icon className="h-3.5 w-3.5" style={{ color }} />{label}</span>
        <span className="font-black tabular-nums text-white">{value}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/10">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${value}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

function List({ icon: Icon, color, title, items }: { icon: React.ElementType; color: string; title: string; items: string[] }) {
  return (
    <div>
      <p className={cn("mb-1.5 flex items-center gap-1.5 text-xs font-bold", color)}><Icon className="h-3.5 w-3.5" />{title}</p>
      <ul className="space-y-1">
        {items.map((s, i) => <li key={i} className="text-xs leading-snug text-slate-300">・{s}</li>)}
      </ul>
    </div>
  );
}

function Chip({ icon: Icon, color, children }: { icon: React.ElementType; color: string; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-xs text-slate-300">
      <Icon className={cn("h-3.5 w-3.5", color)} />{children}
    </span>
  );
}
