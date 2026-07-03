"use client";

import { useRouter } from "next/navigation";
import { useRequireAuth } from "@/hooks/use-require-auth";
import { useMyTeams } from "@/features/teams/hooks/use-teams";
import { useCreateLFP } from "@/features/lfp/hooks/use-lfp";
import { LFPForm } from "../_components/lfp-form";

export default function LFPNewPage() {
  const { ready, authed } = useRequireAuth();
  const router = useRouter();
  const { data: teams, isLoading: teamsLoading } = useMyTeams();
  const create = useCreateLFP();

  if (!ready || !authed) return null;

  if (teamsLoading) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  if (!teams || teams.length === 0) {
    return (
      <div className="mx-auto max-w-lg px-4 py-20 text-center">
        <p className="text-slate-400">募集を作成するにはチームオーナーである必要があります。</p>
        <a href="/teams/create" className="mt-4 inline-block rounded-xl bg-brand-500 px-5 py-2 text-sm font-bold text-white hover:bg-brand-600 transition-colors">
          チームを作成
        </a>
      </div>
    );
  }

  return (
    <LFPForm
      teams={teams}
      onSubmit={async (data) => {
        const res = await create.mutateAsync(data);
        router.push(`/scout/lfp/${res.data.id}`);
      }}
      isSubmitting={create.isPending}
      error={create.isError ? (create.error instanceof Error ? create.error.message : "作成に失敗しました") : undefined}
    />
  );
}
