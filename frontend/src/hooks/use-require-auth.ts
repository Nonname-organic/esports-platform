"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore, type UserRole } from "@/store/auth-store";

export function useRequireAuth(requiredRole?: UserRole | UserRole[]) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, user, _hasHydrated } = useAuthStore();

  useEffect(() => {
    if (!_hasHydrated) return;

    if (!isAuthenticated || !user) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }

    if (requiredRole) {
      const roles = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
      if (!roles.includes(user.role) && user.role !== "admin") {
        router.replace("/tournaments");
      }
    }
  }, [_hasHydrated, isAuthenticated, user, router, pathname, requiredRole]);

  return { authed: isAuthenticated && !!user, user, ready: _hasHydrated };
}
