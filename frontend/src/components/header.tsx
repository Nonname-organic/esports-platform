"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Trophy, LayoutDashboard, BarChart3, LogOut, LogIn, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth-store";
import { NotificationBell } from "@/components/notification-bell";

export function Header() {
  const pathname = usePathname();
  const { user, isAuthenticated, logout } = useAuthStore();

  const navLinks = [
    { href: "/tournaments", label: "大会一覧", icon: Trophy },
    ...(isAuthenticated
      ? [
          { href: "/dashboard", label: "ダッシュボード", icon: LayoutDashboard },
          { href: "/analytics", label: "分析", icon: BarChart3 },
        ]
      : []),
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-slate-950/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 font-bold text-white">
          <Trophy className="h-5 w-5 text-brand-500" />
          <span className="hidden sm:block">EsportsPlatform</span>
        </Link>

        <nav className="flex items-center gap-1">
          {navLinks.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                pathname.startsWith(href)
                  ? "bg-white/10 text-white"
                  : "text-slate-400 hover:bg-white/5 hover:text-white",
              )}
            >
              <Icon className="h-4 w-4" />
              <span className="hidden sm:block">{label}</span>
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <Link
            href="/scout"
            className="rounded-lg p-2 text-slate-400 hover:bg-white/5 hover:text-white transition-colors"
            aria-label="スカウト"
          >
            <Search className="h-5 w-5" />
          </Link>
          <NotificationBell />
          {isAuthenticated && user ? (
            <div className="flex items-center gap-2">
              <div className="hidden sm:block text-right">
                <p className="text-xs font-semibold text-white">{user.username}</p>
                <p className="text-[10px] text-slate-500">{user.role}</p>
              </div>
              {user.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt={user.username}
                  className="h-7 w-7 rounded-full object-cover"
                />
              ) : (
                <div className="h-7 w-7 rounded-full bg-brand-500/20 flex items-center justify-center">
                  <span className="text-xs font-bold text-brand-400">
                    {user.username[0].toUpperCase()}
                  </span>
                </div>
              )}
              <button
                onClick={logout}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-white/5 hover:text-white transition-colors"
                aria-label="ログアウト"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="flex items-center gap-1.5 rounded-lg bg-brand-500 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-600 transition-colors"
            >
              <LogIn className="h-4 w-4" />
              <span>ログイン</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
