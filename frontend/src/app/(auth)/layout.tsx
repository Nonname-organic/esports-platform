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

// 誰でも見える
const PUBLIC_NAV = [
  { href: "/tournaments", label: "大会一覧", icon: Trophy },
  { href: "/scout", label: "スカウト", icon: Search },
  { href: "/analytics", label: "統計分析", icon: BarChart3 },
];

// ログインユーザー向け
const ACCOUNT_NAV = [
  { href: "/teams/create", label: "チームを作成", icon: Plus },
  { href: "/players/create", label: "プレイヤー登録", icon: Users },
  { href: "/discord-link", label: "Discord連携", icon: Link2 },
  { href: "/settings", label: "設定", icon: Settings },
];

// 大会開催者・Admin向け
const ORGANIZER_NAV = [
  { href: "/dashboard", label: "ダッシュボード", icon: LayoutDashboard },
  { href: "/organizer/tournaments/create", label: "大会を作成", icon: Plus },
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

  if (!_hasHydrated) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  const authed = isAuthenticated && !!user;
  const isOrganizer = authed && (user!.role === "organizer" || user!.role === "admin");
  const isAdmin = authed && user!.role === "admin";

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

          {/* ユーザー情報 / ログインボタン */}
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
                <Link href={`/login?next=${encodeURIComponent(pathname)}`}
                  className="flex items-center justify-center gap-1.5 rounded-lg border border-brand-500/40 bg-brand-500/10 px-3 py-2 text-sm font-semibold text-brand-400 hover:bg-brand-500/20 transition-colors">
                  <LogIn className="h-4 w-4" /> ログイン / 新規登録
                </Link>
              )}
            </div>
          )}

          {/* 全体 */}
          <nav className="space-y-1">{PUBLIC_NAV.map(renderLink)}</nav>

          {/* ログインユーザー向け */}
          {authed && (
            <div className="mt-4 space-y-1 border-t border-white/10 pt-4">
              {!collapsed && (
                <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-slate-600">アカウント</p>
              )}
              {ACCOUNT_NAV.map(renderLink)}
            </div>
          )}

          {/* 大会開催者・Admin向け */}
          {isOrganizer && (
            <div className="mt-4 space-y-1 border-t border-white/10 pt-4">
              {!collapsed && (
                <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-slate-600">主催者</p>
              )}
              {ORGANIZER_NAV.map(renderLink)}
            </div>
          )}

          {/* Admin限定 */}
          {isAdmin && (
            <div className="mt-4 space-y-1 border-t border-white/10 pt-4">
              {!collapsed && (
                <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-red-800">Admin</p>
              )}
              {renderLink({ href: "/admin", label: "Admin Dashboard", icon: Shield })}
            </div>
          )}
        </div>
      </aside>

      {/* メインコンテンツ：常に表示 */}
      <div className="flex-1 min-w-0">
        {children}
      </div>
    </div>
  );
}
