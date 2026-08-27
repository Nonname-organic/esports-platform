"use client";

import { useEffect } from "react";
import { AlertTriangle, X } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * 取り消しづらい操作の前に出す確認ダイアログ。
 * 見出し・本文・注意書きを分けて表示し、何が起きるかを読ませてから実行させる。
 */
export function ConfirmDialog({
  open,
  title,
  description,
  notes,
  confirmLabel = "実行する",
  cancelLabel = "キャンセル",
  tone = "warning",
  busy,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description?: React.ReactNode;
  /** 箇条書きの注意事項 */
  notes?: React.ReactNode[];
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "warning" | "danger";
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  // Escape で閉じる（誤操作からの離脱を簡単にする）
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onCancel(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  if (!open) return null;

  const accent = tone === "danger" ? "text-red-400" : "text-yellow-400";
  const confirmCls = tone === "danger"
    ? "bg-red-500 hover:bg-red-600"
    : "bg-brand-500 hover:bg-brand-600";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onCancel}
    >
      <div
        className="w-full max-w-md rounded-2xl border border-white/10 bg-slate-900 p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-start gap-3">
          <div className={cn("rounded-lg bg-white/5 p-2", accent)}>
            <AlertTriangle className="h-5 w-5" />
          </div>
          <h2 className="flex-1 pt-1.5 text-base font-bold text-white">{title}</h2>
          <button
            type="button"
            onClick={onCancel}
            aria-label="閉じる"
            className="rounded-lg p-1.5 text-slate-500 hover:bg-white/5 hover:text-white transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {description && (
          <div className="mb-3 text-sm leading-relaxed text-slate-300">{description}</div>
        )}

        {notes && notes.length > 0 && (
          <ul className="mb-4 space-y-1.5 rounded-xl border border-white/8 bg-white/[0.03] p-3">
            {notes.map((n, i) => (
              <li key={i} className="flex gap-2 text-xs leading-relaxed text-slate-400">
                <span className="text-slate-600">・</span>
                <span>{n}</span>
              </li>
            ))}
          </ul>
        )}

        <div className="flex gap-2">
          <button
            type="button"
            onClick={onConfirm}
            disabled={busy}
            className={cn(
              "flex-1 rounded-xl py-2.5 text-sm font-bold text-white transition-colors disabled:opacity-40",
              confirmCls,
            )}
          >
            {busy ? "処理中..." : confirmLabel}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="rounded-xl border border-white/10 px-5 py-2.5 text-sm text-slate-400 hover:text-white transition-colors"
          >
            {cancelLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
