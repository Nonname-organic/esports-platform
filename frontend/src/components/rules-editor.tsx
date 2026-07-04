"use client";

import { useEffect, useState } from "react";
import { Loader2, Save, Check, Eye, EyeOff, Sparkles } from "lucide-react";
import {
  useRules,
  useRulesTemplates,
  useUpdateRules,
  useApplyRulesTemplate,
} from "@/features/rules/hooks/use-rules";
import type { RulesSection } from "@/features/rules/api/rules-api";
import { SimpleMarkdown } from "@/components/simple-markdown";

/** 主催者向けルール編集（固定Section構造 + テンプレート適用）。 */
export function RulesEditor({ tournamentId }: { tournamentId: string }) {
  const { data: doc, isLoading } = useRules(tournamentId);
  const { data: templates } = useRulesTemplates();
  const update = useUpdateRules(tournamentId);
  const applyTemplate = useApplyRulesTemplate(tournamentId);

  const [sections, setSections] = useState<RulesSection[]>([]);
  const [preview, setPreview] = useState(false);
  const [templateId, setTemplateId] = useState("");
  const [confirmApply, setConfirmApply] = useState(false);

  // サーバーのdoc（未設定なら全固定Sectionの空雛形）をローカル編集状態へ反映
  useEffect(() => {
    if (doc?.sections) {
      setSections([...doc.sections].sort((a, b) => a.order - b.order));
    }
  }, [doc]);

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-brand-500" />
      </div>
    );
  }

  const setBody = (id: string, body_md: string) =>
    setSections((prev) => prev.map((s) => (s.id === id ? { ...s, body_md } : s)));

  const save = () => update.mutate({ sections });

  const doApplyTemplate = () => {
    if (!templateId) return;
    applyTemplate.mutate(templateId, { onSuccess: () => setConfirmApply(false) });
  };

  return (
    <div className="space-y-4">
      {/* テンプレート適用 */}
      <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <h3 className="mb-1 flex items-center gap-2 text-sm font-bold text-white">
          <Sparkles className="h-4 w-4 text-brand-400" />
          テンプレートから適用
        </h3>
        <p className="mb-3 text-xs text-slate-500">
          既存の入力内容はテンプレートで上書きされます。
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={templateId}
            onChange={(e) => { setTemplateId(e.target.value); setConfirmApply(false); }}
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-brand-500"
          >
            <option value="">テンプレートを選択…</option>
            {(templates ?? []).map((t) => (
              <option key={t.id} value={t.id}>
                {t.label}{t.game ? `（${t.game}）` : ""}
              </option>
            ))}
          </select>
          {!confirmApply ? (
            <button
              type="button"
              onClick={() => setConfirmApply(true)}
              disabled={!templateId}
              className="rounded-lg bg-brand-500/10 px-3 py-2 text-sm font-semibold text-brand-400 hover:bg-brand-500/20 disabled:opacity-40"
            >
              適用
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-xs text-yellow-400">上書きしますか？</span>
              <button
                type="button"
                onClick={doApplyTemplate}
                disabled={applyTemplate.isPending}
                className="flex items-center gap-1.5 rounded-lg bg-brand-500 px-3 py-2 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50"
              >
                {applyTemplate.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                上書きする
              </button>
              <button
                type="button"
                onClick={() => setConfirmApply(false)}
                className="rounded-lg border border-white/10 px-3 py-2 text-sm text-slate-400 hover:text-white"
              >
                キャンセル
              </button>
            </div>
          )}
        </div>
        {applyTemplate.isError && (
          <p className="mt-2 text-xs text-red-400">
            {applyTemplate.error instanceof Error ? applyTemplate.error.message : "適用に失敗しました"}
          </p>
        )}
      </div>

      {/* 編集ツールバー */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setPreview((v) => !v)}
          className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:text-white"
        >
          {preview ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
          {preview ? "編集に戻る" : "プレビュー"}
        </button>
        <div className="flex items-center gap-2">
          {update.isSuccess && !update.isPending && (
            <span className="flex items-center gap-1 text-xs text-green-400">
              <Check className="h-3.5 w-3.5" /> 保存しました
            </span>
          )}
          <button
            type="button"
            onClick={save}
            disabled={update.isPending}
            className="flex items-center gap-2 rounded-lg bg-brand-500 px-4 py-2 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50"
          >
            {update.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            保存
          </button>
        </div>
      </div>
      {update.isError && (
        <p className="text-xs text-red-400">
          {update.error instanceof Error ? update.error.message : "保存に失敗しました"}
        </p>
      )}

      {/* 各Section（固定id順） */}
      <div className="space-y-4">
        {sections.map((s) => (
          <div key={s.id} className="rounded-xl border border-white/10 bg-slate-900 p-5">
            <label className="mb-2 block text-sm font-bold text-white">{s.title}</label>
            {preview ? (
              s.body_md.trim() ? (
                <div className="rounded-lg border border-white/8 bg-white/3 p-4">
                  <SimpleMarkdown source={s.body_md} />
                </div>
              ) : (
                <p className="text-xs text-slate-600">（未入力）</p>
              )
            ) : (
              <textarea
                value={s.body_md}
                onChange={(e) => setBody(s.id, e.target.value)}
                rows={6}
                placeholder="Markdownで入力できます（- 箇条書き / **太字** / # 見出し）"
                className="w-full resize-y rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm leading-relaxed text-slate-200 placeholder-slate-600 outline-none focus:border-brand-500"
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
