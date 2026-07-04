"use client";

import { useEntityTags } from "@/features/tags/hooks/use-tags";
import { TagList } from "@/components/tag-badge";

export function TeamTags({ teamId }: { teamId: string }) {
  const { data: tags } = useEntityTags("team", teamId);
  if (!tags || tags.length === 0) return null;
  return <div className="mt-2"><TagList tags={tags} /></div>;
}
