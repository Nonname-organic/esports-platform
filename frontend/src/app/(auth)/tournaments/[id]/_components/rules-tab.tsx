"use client";

import { ScrollText, Loader2 } from "lucide-react";
import { useRules } from "@/features/rules/hooks/use-rules";
import { SimpleMarkdown } from "@/components/simple-markdown";

export function RulesTab({ tournamentId }: { tournamentId: string }) {
  const { data: doc, isLoading } = useRules(tournamentId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-brand-500" />
      </div>
    );
  }

  const sections = (doc?.sections ?? [])
    .filter((s) => s.body_md.trim().length > 0)
    .sort((a, b) => a.order - b.order);

  if (sections.length === 0) {
    return (
      <div className="flex h-48 flex-col items-center justify-center pt-6 text-center">
        <ScrollText className="mb-3 h-10 w-10 text-slate-700" />
        <p className="text-sm text-slate-500">ルールはまだ公開されていません。</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 pt-6">
      {sections.map((s) => (
        <section key={s.id} className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h2 className="mb-3 flex items-center gap-2 font-bold text-white">
            <ScrollText className="h-4 w-4 text-brand-400" />
            {s.title}
          </h2>
          <SimpleMarkdown source={s.body_md} />
        </section>
      ))}
    </div>
  );
}
