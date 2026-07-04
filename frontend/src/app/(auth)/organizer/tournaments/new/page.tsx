"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * 旧・簡易大会作成フォームは廃止。
 * サイドバー/ダッシュボードと同じ正式フォーム（/create）へリダイレクトする。
 */
export default function TournamentNewRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/organizer/tournaments/create");
  }, [router]);

  return (
    <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
    </div>
  );
}
