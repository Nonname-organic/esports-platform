import { cn } from "@/lib/utils";
import type { Tag } from "@/features/tags/api/tag-api";

export function TagBadge({ tag, onRemove }: { tag: Tag; onRemove?: () => void }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium",
        "border-brand-500/30 bg-brand-500/10 text-brand-300",
      )}
      style={tag.color ? { borderColor: `${tag.color}55`, color: tag.color } : undefined}
    >
      {tag.label}
      {onRemove && (
        <button type="button" onClick={onRemove} className="ml-0.5 opacity-60 hover:opacity-100" aria-label="削除">
          ×
        </button>
      )}
    </span>
  );
}

export function TagList({ tags }: { tags?: Tag[] }) {
  if (!tags || tags.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {tags.map((t) => <TagBadge key={t.id} tag={t} />)}
    </div>
  );
}
