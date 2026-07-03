"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import { useRequireAuth } from "@/hooks/use-require-auth";
import { useMyTeams } from "@/features/teams/hooks/use-teams";
import { useLFP, useUpdateLFP } from "@/features/lfp/hooks/use-lfp";
import { LFPForm } from "../../_components/lfp-form";

export default function LFPEditPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { ready, authed } = useRequireAuth();
  const router = useRouter();
  const { data: post, isLoading: postLoading } = useLFP(id);
  const { data: teams, isLoading: teamsLoading } = useMyTeams();
  const update = useUpdateLFP(id);

  if (!ready || !authed) return null;

  if (postLoading || teamsLoading) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  if (!post || !teams) return null;

  return (
    <LFPForm
      teams={teams}
      defaultValues={post}
      onSubmit={async (data) => {
        await update.mutateAsync(data);
        router.push(`/scout/lfp/${id}`);
      }}
      isSubmitting={update.isPending}
      error={update.isError ? (update.error instanceof Error ? update.error.message : "更新に失敗しました") : undefined}
    />
  );
}
