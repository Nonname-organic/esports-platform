"use client";

import { useState } from "react";
import { Loader2, Plus, Check } from "lucide-react";
import { useEntityTags, useSetEntityTags, useTagCatalog } from "@/features/tags/hooks/use-tags";
import type { TagEntityType } from "@/features/tags/api/tag-api";
import { TagBadge } from "@/components/tag-badge";

/** エンティティのタグ編集（owner/organizer 等が使用）。差し替え PUT で保存。 */
export function TagEditor({ entityType, entityId }: { entityType: TagEntityType; entityId: string }) {
  const { data: current } = useEntityTags(entityType, entityId);
  const { data: catalog } = useTagCatalog();
  const save = useSetEntityTags(entityType, entityId);
  const [input, setInput] = useState("");

  const labels = (current ?? []).map((t) => t.label);

  const commit = (next: string[]) => save.mutate(Array.from(new Set(next)));

  const add = (label: string) => {
    const v = label.trim();
    if (!v || labels.some((l) => l.toLowerCase() === v.toLowerCase())) { setInput(""); return; }
    commit([...labels, v]);
    setInput("");
  };
  const remove = (label: string) => commit(labels.filter((l) => l !== label));

  const suggestions = (catalog ?? [])
    .filter((t) => input && t.label.toLowerCase().includes(input.toLowerCase()))
    .filter((t) => !labels.some((l) => l.toLowerCase() === t.label.toLowerCase()))
    .slice(0, 6);

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-1.5">
        {(current ?? []).map((t) => (
          <TagBadge key={t.id} tag={t} onRemove={() => remove(t.label)} />
        ))}
        {save.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin text-slate-500" />}
        {save.isSuccess && !save.isPending && <Check className="h-3.5 w-3.5 text-green-400" />}
      </div>

      <div className="relative">
        <div className="flex items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(input); } }}
            placeholder="タグを追加（Enterで確定）"
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-white placeholder-slate-600 outline-none focus:border-brand-500"
          />
          <button type="button" onClick={() => add(input)} disabled={!input.trim()}
            className="flex items-center gap-1 rounded-lg bg-brand-500/10 px-2.5 py-1.5 text-xs font-semibold text-brand-400 hover:bg-brand-500/20 disabled:opacity-40">
            <Plus className="h-3.5 w-3.5" />
          </button>
        </div>
        {suggestions.length > 0 && (
          <div className="absolute z-10 mt-1 w-full rounded-lg border border-white/10 bg-slate-900 p-1 shadow-xl">
            {suggestions.map((t) => (
              <button key={t.id} type="button" onClick={() => add(t.label)}
                className="block w-full rounded-md px-2.5 py-1.5 text-left text-sm text-slate-300 hover:bg-white/5">
                {t.label}
              </button>
            ))}
          </div>
        )}
      </div>
      {save.isError && (
        <p className="text-xs text-red-400">{save.error instanceof Error ? save.error.message : "保存に失敗しました"}</p>
      )}
    </div>
  );
}
