"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { LayoutDashboard, BarChart3, Plus, Shield, Users } from "lucide-react";
import { useAuthStore } from "@/store/auth-store";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", label: "ダッシュボード", icon: LayoutDashboard },
  { href: "/analytics", label: "統計分析", icon: BarChart3 },
];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, user, _hasHydrated } = useAuthStore();

  // _hasHydrated: Zustand persist がlocalStorageから読み込み完了したタイミング
  useEffect(() => {
    if (_hasHydrated && !isAuthenticated) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [_hasHydrated, isAuthenticated, router, pathname]);

  // localStorage読み込み完了前 or 未認証はスピナー表示
  if (!_hasHydrated || !isAuthenticated || !user) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)]">
      {/* サイドバー */}
      <aside className="hidden w-56 shrink-0 border-r border-white/10 bg-slate-900/50 lg:block">
        <div className="sticky top-14 p-4">
          {/* ユーザー情報 */}
          <div className="mb-6 rounded-xl bg-white/5 p-3">
            <div className="flex items-center gap-2.5">
              {user.avatar_url ? (
                <img src={user.avatar_url} alt={user.username} className="h-8 w-8 rounded-full object-cover" />
              ) : (
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-500/20">
                  <span className="text-sm font-bold text-brand-400">
                    {user.username[0].toUpperCase()}
                  </span>
                </div>
              )}
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-white">{user.username}</p>
                <p className="text-xs text-slate-500">{user.role}</p>
              </div>
            </div>
          </div>

          {/* ナビゲーション */}
          <nav className="space-y-1">
            {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  pathname === href
                    ? "bg-brand-500/20 text-brand-400"
                    : "text-slate-400 hover:bg-white/5 hover:text-white",
                )}
              >
                <Icon className="h-4 w-4 flex-shrink-0" />
                {label}
              </Link>
            ))}
          </nav>

          {/* チームメニュー（全ユーザー） */}
          <div className="mt-6 border-t border-white/10 pt-6">
            <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-slate-600">
              チーム
            </p>
            <Link
              href="/teams/create"
              className={cn(
                "flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                pathname === "/teams/create"
                  ? "bg-brand-500/20 text-brand-400"
                  : "text-slate-400 hover:bg-white/5 hover:text-white",
              )}
            >
              <Plus className="h-4 w-4 flex-shrink-0" />
              チームを作成
            </Link>
            <Link
              href="/players/create"
              className={cn(
                "flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                pathname === "/players/create"
                  ? "bg-brand-500/20 text-brand-400"
                  : "text-slate-400 hover:bg-white/5 hover:text-white",
              )}
            >
              <Users className="h-4 w-4 flex-shrink-0" />
              プレイヤー登録
            </Link>
          </div>

          {/* 主催者向けアクション */}
          {(user.role === "organizer" || user.role === "admin") && (
            <div className="mt-4 border-t border-white/10 pt-4">
              <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-slate-600">
                主催者メニュー
              </p>
              <Link
                href="/organizer/tournaments/create"
                className={cn(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  pathname.startsWith("/organizer/tournaments/create")
                    ? "bg-brand-500/20 text-brand-400"
                    : "text-slate-400 hover:bg-white/5 hover:text-white",
                )}
              >
                <Plus className="h-4 w-4 flex-shrink-0" />
                大会を作成
              </Link>
            </div>
          )}

          {/* Admin専用メニュー */}
          {user.role === "admin" && (
            <div className="mt-4 border-t border-white/10 pt-4">
              <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-red-800">
                Admin
              </p>
              <Link
                href="/admin"
                className={cn(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  pathname === "/admin"
                    ? "bg-red-500/10 text-red-400"
                    : "text-slate-500 hover:bg-red-500/5 hover:text-red-400",
                )}
              >
                <Shield className="h-4 w-4 flex-shrink-0" />
                Admin Dashboard
              </Link>
            </div>
          )}
        </div>
      </aside>

      {/* メインコンテンツ */}
      <div className="flex-1 min-w-0">
        {children}
      </div>
    </div>
  );
}
