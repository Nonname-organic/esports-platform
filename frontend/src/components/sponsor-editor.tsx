"use client";

import { useState } from "react";
import { Plus, Trash2, Loader2, ExternalLink } from "lucide-react";
import { useSponsors, useCreateSponsor, useDeleteSponsor } from "@/features/sponsors/hooks/use-sponsors";
import { ImageUpload } from "@/components/image-upload";

const inputCls = "w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-slate-600 outline-none focus:border-brand-500";

export function SponsorEditor({ teamId }: { teamId: string }) {
  const { data: sponsors, isLoading } = useSponsors(teamId);
  const create = useCreateSponsor(teamId);
  const remove = useDeleteSponsor(teamId);

  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [type, setType] = useState("");
  const [logo, setLogo] = useState("");

  const add = () => {
    if (!name.trim()) return;
    create.mutate(
      { name: name.trim(), url: url.trim() || undefined, sponsor_type: type.trim() || undefined, logo_url: logo || undefined, display_order: sponsors?.length ?? 0 },
      { onSuccess: () => { setName(""); setUrl(""); setType(""); setLogo(""); } },
    );
  };

  return (
    <div className="space-y-3">
      {isLoading ? (
        <div className="h-16 animate-pulse rounded-lg bg-white/5" />
      ) : (
        (sponsors ?? []).map((s) => (
          <div key={s.id} className="flex items-center gap-3 rounded-lg border border-white/8 bg-white/3 px-3 py-2">
            <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center overflow-hidden rounded-md border border-white/10 bg-slate-800">
              {s.logo_url ? <img src={s.logo_url} alt="" className="h-full w-full object-contain" /> : <span className="text-[10px] text-slate-500">{s.name.slice(0, 2)}</span>}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-white">{s.name}</p>
              <p className="truncate text-xs text-slate-500">{s.sponsor_type ?? "スポンサー"}{s.url ? ` · ${s.url}` : ""}</p>
            </div>
            <button onClick={() => remove.mutate(s.id)} disabled={remove.isPending}
              className="rounded-md p-1.5 text-slate-500 hover:bg-white/5 hover:text-red-400 disabled:opacity-50" aria-label="削除">
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))
      )}

      {/* 追加フォーム */}
      <div className="space-y-2 rounded-lg border border-dashed border-white/15 p-3">
        <div className="grid grid-cols-2 gap-2">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="スポンサー名 *" className={inputCls} />
          <input value={type} onChange={(e) => setType(e.target.value)} placeholder="種別（title/gold等）" className={inputCls} />
        </div>
        <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="URL（任意）" className={inputCls} />
        <ImageUpload value={logo} onChange={setLogo} purpose="team_logo" label="ロゴ（任意）" aspectRatio="square" />
        <button onClick={add} disabled={!name.trim() || create.isPending}
          className="flex items-center gap-1.5 rounded-lg bg-brand-500/10 px-3 py-2 text-sm font-semibold text-brand-400 hover:bg-brand-500/20 disabled:opacity-40">
          {create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />} スポンサーを追加
        </button>
        {create.isError && <p className="text-xs text-red-400">{create.error instanceof Error ? create.error.message : "追加に失敗しました"}</p>}
      </div>
    </div>
  );
}
