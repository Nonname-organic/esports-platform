"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, X, Clock, Shield, User, Trophy, Swords, Loader2 } from "lucide-react";
import { useGlobalSearch } from "@/features/search/hooks/use-search";
import { useSearchStore } from "@/store/search-store";
import type { SearchHit } from "@/features/search/api/search-api";
import { cn } from "@/lib/utils";

const TYPE_META: Record<string, { label: string; icon: React.ElementType }> = {
  team: { label: "チーム", icon: Shield },
  player: { label: "プレイヤー", icon: User },
  tournament: { label: "大会", icon: Trophy },
  match: { label: "試合", icon: Swords },
};

export function GlobalSearch() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data, isFetching } = useGlobalSearch(q);
  const { recentQueries, recentlyViewed, addQuery, addViewed } = useSearchStore();

  // 外クリックで閉じる
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  // ⌘K / Ctrl+K でフォーカス
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
        setOpen(true);
      }
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const go = (hit: { type: string; id: string; label: string; url: string }) => {
    addQuery(q);
    addViewed({ type: hit.type, id: hit.id, label: hit.label, url: hit.url });
    setOpen(false);
    setQ("");
    router.push(hit.url);
  };

  const groups: { type: string; hits: SearchHit[] }[] = data
    ? [
        { type: "team", hits: data.teams },
        { type: "player", hits: data.players },
        { type: "tournament", hits: data.tournaments },
        { type: "match", hits: data.matches },
      ].filter((g) => g.hits.length > 0)
    : [];

  const hasResults = groups.length > 0;
  const showRecent = q.trim().length < 2;

  return (
    <div ref={ref} className="relative w-full max-w-xs">
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        <input
          ref={inputRef}
          value={q}
          onChange={(e) => { setQ(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          placeholder="検索 (⌘K)"
          className="w-full rounded-lg border border-white/10 bg-white/5 py-1.5 pl-9 pr-8 text-sm text-white placeholder-slate-600 outline-none focus:border-brand-500 transition-colors"
        />
        {isFetching ? (
          <Loader2 className="absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 animate-spin text-slate-500" />
        ) : q ? (
          <button onClick={() => { setQ(""); inputRef.current?.focus(); }}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white">
            <X className="h-3.5 w-3.5" />
          </button>
        ) : null}
      </div>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-80 overflow-hidden rounded-xl border border-white/10 bg-slate-900 shadow-2xl">
          {showRecent ? (
            <div className="max-h-96 overflow-y-auto p-2">
              {recentlyViewed.length > 0 && (
                <Section title="最近見た項目">
                  {recentlyViewed.map((it) => (
                    <Row key={`${it.type}-${it.id}`} type={it.type} label={it.label} sub={null} image={null}
                      onClick={() => go(it)} />
                  ))}
                </Section>
              )}
              {recentQueries.length > 0 && (
                <Section title="検索履歴">
                  {recentQueries.map((rq) => (
                    <button key={rq} onClick={() => { setQ(rq); }}
                      className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm text-slate-300 hover:bg-white/5">
                      <Clock className="h-3.5 w-3.5 text-slate-600" /> {rq}
                    </button>
                  ))}
                </Section>
              )}
              {recentlyViewed.length === 0 && recentQueries.length === 0 && (
                <p className="px-3 py-6 text-center text-xs text-slate-600">2文字以上で検索</p>
              )}
            </div>
          ) : hasResults ? (
            <div className="max-h-96 overflow-y-auto p-2">
              {groups.map((g) => (
                <Section key={g.type} title={TYPE_META[g.type].label}>
                  {g.hits.map((h) => (
                    <Row key={`${h.type}-${h.id}`} type={h.type} label={h.label} sub={h.sub} image={h.image_url}
                      onClick={() => go(h)} />
                  ))}
                </Section>
              ))}
            </div>
          ) : (
            <p className="px-3 py-6 text-center text-xs text-slate-600">
              {isFetching ? "検索中..." : `「${q}」に一致する結果がありません`}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-1">
      <p className="px-2.5 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-widest text-slate-600">{title}</p>
      {children}
    </div>
  );
}

function Row({ type, label, sub, image, onClick }: {
  type: string; label: string; sub: string | null; image: string | null; onClick: () => void;
}) {
  const Icon = TYPE_META[type]?.icon ?? Search;
  return (
    <button onClick={onClick}
      className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left hover:bg-white/5 transition-colors">
      <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center overflow-hidden rounded-md border border-white/10 bg-slate-800">
        {image ? <img src={image} alt="" className="h-full w-full object-contain" /> : <Icon className="h-3.5 w-3.5 text-slate-400" />}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm text-white">{label}</p>
        {sub && <p className="truncate text-xs text-slate-500">{sub}</p>}
      </div>
    </button>
  );
}
