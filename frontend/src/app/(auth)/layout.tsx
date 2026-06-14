"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  LayoutDashboard, BarChart3, Plus, Shield, Users, Link2, Trophy, Search, Settings,
  LogIn, ChevronsLeft, ChevronsRight,
} from "lucide-react";
import { useAuthStore } from "@/store/auth-store";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", label: "ダッシュボード", icon: LayoutDashboard },
  { href: "/tournaments", label: "大会一覧", icon: Trophy },
  { href: "/scout", label: "スカウト", icon: Search },
  { href: "/analytics", label: "統計分析", icon: BarChart3 },
];

const ACCOUNT_ITEMS = [
  { href: "/teams/create", label: "チームを作成", icon: Plus },
  { href: "/players/create", label: "プレイヤー登録", icon: Users },
  { href: "/discord-link", label: "Discord連携", icon: Link2 },
  { href: "/settings", label: "設定", icon: Settings },
];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { isAuthenticated, user, _hasHydrated } = useAuthStore();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    try { setCollapsed(localStorage.getItem("sidebar-collapsed") === "1"); } catch { /* ignore */ }
  }, []);

  const toggle = () => setCollapsed((c) => {
    const next = !c;
    try { localStorage.setItem("sidebar-collapsed", next ? "1" : "0"); } catch { /* ignore */ }
    return next;
  });

  // localStorage読み込み完了前はスピナー（チラつき防止）
  if (!_hasHydrated) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  const authed = isAuthenticated && !!user;

  const renderLink = ({ href, label, icon: Icon }: { href: string; label: string; icon: React.ElementType }) => (
    <Link
      key={href}
      href={href}
      title={collapsed ? label : undefined}
      className={cn(
        "flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
        collapsed && "justify-center px-0",
        pathname === href ? "bg-brand-500/20 text-brand-400" : "text-slate-400 hover:bg-white/5 hover:text-white",
      )}
    >
      <Icon className="h-4 w-4 flex-shrink-0" />
      {!collapsed && <span className="truncate">{label}</span>}
    </Link>
  );

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)]">
      {/* サイドバー（折りたたみ可） */}
      <aside
        className={cn(
          "hidden shrink-0 border-r border-white/10 bg-slate-900/50 transition-[width] duration-200 lg:block",
          collapsed ? "w-16" : "w-56",
        )}
      >
        <div className="sticky top-14 p-3">
          {/* 折りたたみトグル */}
          <button
            onClick={toggle}
            className="mb-3 flex w-full items-center justify-center rounded-lg px-2 py-1.5 text-slate-500 hover:bg-white/5 hover:text-white transition-colors"
            title={collapsed ? "サイドバーを展開" : "サイドバーを最小化"}
            aria-label={collapsed ? "展開" : "最小化"}
          >
            {collapsed ? <ChevronsRight className="h-4 w-4" /> : (
              <span className="flex items-center gap-1 text-xs"><ChevronsLeft className="h-4 w-4" /> 最小化</span>
            )}
          </button>

          {/* ユーザー / ログイン案内 */}
          {authed ? (
            <div className={cn("mb-4 rounded-xl bg-white/5", collapsed ? "p-2" : "p-3")}>
              <div className={cn("flex items-center gap-2.5", collapsed && "justify-center")}>
                {user!.avatar_url ? (
                  <img src={user!.avatar_url} alt={user!.username} className="h-8 w-8 rounded-full object-cover" />
                ) : (
                  <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-brand-500/20">
                    <span className="text-sm font-bold text-brand-400">{user!.username[0].toUpperCase()}</span>
                  </div>
                )}
                {!collapsed && (
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-white">{user!.username}</p>
                    <p className="text-xs text-slate-500">{user!.role}</p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="mb-4">
              {collapsed ? (
                <Link href={`/login?next=${encodeURIComponent(pathname)}`} title="ログイン"
                  className="flex items-center justify-center rounded-lg bg-brand-500 p-2 text-white hover:bg-brand-600 transition-colors">
                  <LogIn className="h-4 w-4" />
                </Link>
              ) : (
                <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-center">
                  <p className="mb-2 text-xs text-slate-400">ログインが必要です</p>
                  <Link href={`/login?next=${encodeURIComponent(pathname)}`}
                    className="flex items-center justify-center gap-1.5 rounded-lg bg-brand-500 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-600 transition-colors">
                    <LogIn className="h-4 w-4" /> ログイン
                  </Link>
                </div>
              )}
            </div>
          )}

          {/* ナビゲーション */}
          <nav className="space-y-1">{NAV_ITEMS.map(renderLink)}</nav>

          <div className="mt-4 space-y-1 border-t border-white/10 pt-4">
            {!collapsed && (
              <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-slate-600">アカウント</p>
            )}
            {ACCOUNT_ITEMS.map(renderLink)}
          </div>

          {authed && (user!.role === "organizer" || user!.role === "admin") && (
            <div className="mt-4 space-y-1 border-t border-white/10 pt-4">
              {!collapsed && (
                <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-slate-600">主催者</p>
              )}
              {renderLink({ href: "/organizer/tournaments/create", label: "大会を作成", icon: Plus })}
            </div>
          )}

          {authed && user!.role === "admin" && (
            <div className="mt-4 space-y-1 border-t border-white/10 pt-4">
              {!collapsed && (
                <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-red-800">Admin</p>
              )}
              {renderLink({ href: "/admin", label: "Admin Dashboard", icon: Shield })}
            </div>
          )}
        </div>
      </aside>

      {/* メインコンテンツ */}
      <div className="flex-1 min-w-0">
        {authed ? children : (
          <div className="flex h-[calc(100vh-3.5rem)] flex-col items-center justify-center px-4 text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-500/10">
              <LogIn className="h-8 w-8 text-brand-400" />
            </div>
            <h2 className="text-lg font-bold text-white">ログインが必要です</h2>
            <p className="mt-1 text-sm text-slate-400">この画面を表示するにはログインしてください。</p>
            <Link href={`/login?next=${encodeURIComponent(pathname)}`}
              className="mt-6 flex items-center gap-2 rounded-xl bg-brand-500 px-6 py-2.5 text-sm font-bold text-white hover:bg-brand-600 transition-colors">
              <LogIn className="h-4 w-4" /> ログイン / 新規登録
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
