"use client";

import { useRef, useState } from "react";
import { Paperclip, X, Loader2, FileText, AlertCircle } from "lucide-react";
import { tournamentApi } from "@/features/tournaments/api/tournament-api";
import type { TournamentAttachment } from "@/types/tournament";

interface AttachmentUploadProps {
  value: TournamentAttachment[];
  onChange: (files: TournamentAttachment[]) => void;
  maxFiles?: number;
}

function formatSize(bytes?: number): string {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** 大会説明などに添付するファイル（PDF・画像・ドキュメント）のアップロードUI */
export function AttachmentUpload({ value, onChange, maxFiles = 5 }: AttachmentUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const files = value ?? [];

  const handleSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? []);
    if (selected.length === 0) return;
    if (files.length + selected.length > maxFiles) {
      setError(`添付は最大${maxFiles}件までです`);
      return;
    }
    setError(null);
    setUploading(true);
    try {
      const uploaded: TournamentAttachment[] = [];
      for (const file of selected) {
        const res = await tournamentApi.uploadFile(file);
        uploaded.push(res);
      }
      onChange([...files, ...uploaded]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "アップロードに失敗しました");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const remove = (key: string) => onChange(files.filter((f) => f.key !== key));

  return (
    <div className="space-y-3">
      {/* アップロード済みファイル */}
      {files.length > 0 && (
        <ul className="space-y-2">
          {files.map((f) => (
            <li key={f.key} className="flex items-center gap-3 rounded-lg border border-white/10 bg-white/5 px-3 py-2.5">
              <FileText className="h-4 w-4 flex-shrink-0 text-brand-400" />
              <div className="min-w-0 flex-1">
                <a href={f.url} target="_blank" rel="noopener noreferrer" className="block truncate text-sm text-white hover:text-brand-400 transition-colors">
                  {f.name}
                </a>
                {f.size ? <span className="text-xs text-slate-500">{formatSize(f.size)}</span> : null}
              </div>
              <button type="button" onClick={() => remove(f.key)}
                className="rounded-md p-1 text-slate-500 hover:bg-white/5 hover:text-red-400 transition-colors" aria-label="削除">
                <X className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* アップロードボタン */}
      {files.length < maxFiles && (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-white/15 bg-white/3 px-4 py-3 text-sm text-slate-400 hover:border-brand-500/40 hover:text-white disabled:opacity-50 transition-colors"
        >
          {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Paperclip className="h-4 w-4" />}
          {uploading ? "アップロード中..." : "ファイルを添付（PDF・画像・Word・Excel・ZIP / 10MBまで）"}
        </button>
      )}

      <input
        ref={inputRef}
        type="file"
        multiple
        onChange={handleSelect}
        className="hidden"
        accept=".pdf,.jpg,.jpeg,.png,.webp,.gif,.doc,.docx,.xls,.xlsx,.txt,.csv,.zip"
      />

      {error && (
        <p className="flex items-center gap-1 text-xs text-red-400">
          <AlertCircle className="h-3.5 w-3.5" />{error}
        </p>
      )}
    </div>
  );
}
