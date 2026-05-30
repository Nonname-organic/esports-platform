import { cn } from "@/lib/utils";

function Shimmer({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-white/5",
        className,
      )}
    />
  );
}

export function TournamentCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-xl border border-white/10 bg-white/5">
      <Shimmer className="h-32 rounded-none" />
      <div className="p-4 space-y-3">
        <Shimmer className="h-5 w-3/4" />
        <Shimmer className="h-4 w-1/2" />
        <div className="flex items-center justify-between">
          <Shimmer className="h-4 w-1/3" />
          <Shimmer className="h-4 w-1/4" />
        </div>
        <Shimmer className="h-1.5 w-full rounded-full" />
      </div>
    </div>
  );
}

export function TournamentGridSkeleton({ count = 12 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }).map((_, i) => (
        <TournamentCardSkeleton key={i} />
      ))}
    </div>
  );
}
