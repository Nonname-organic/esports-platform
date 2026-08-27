"use client";

import { useEffect, useState } from "react";
import { Info, X } from "lucide-react";

const DISMISS_KEY = "axelia-demo-notice-dismissed";

/**
 * デモ環境であることの告知。
 *
 * 掲載されている大会・チーム・戦績はデモ用に作成したもので、実在の大会の
 * 記録ではない。閲覧者が実績と誤解しないよう明示する。
 * 本番環境では NEXT_PUBLIC_DEMO_MODE を外すことで非表示になる。
 */
export function DemoBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_DEMO_MODE !== "true") return;
    try {
      setVisible(sessionStorage.getItem(DISMISS_KEY) !== "1");
    } catch {
      setVisible(true);
    }
  }, []);

  if (!visible) return null;

  const dismiss = () => {
    setVisible(false);
    try {
      sessionStorage.setItem(DISMISS_KEY, "1");
    } catch {
      /* プライベートモード等では保存できないが、表示自体は消せる */
    }
  };

  return (
    <div className="border-b border-amber-500/25 bg-amber-500/10">
      <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-2">
        <Info className="h-3.5 w-3.5 flex-shrink-0 text-amber-400" />
        <p className="text-[11px] leading-relaxed text-amber-200/90">
          これはデモ環境です。掲載中の大会・チーム・戦績はすべて動作確認用の
          サンプルデータで、実在の大会の記録ではありません。
        </p>
        <button
          type="button"
          onClick={dismiss}
          aria-label="この案内を閉じる"
          className="ml-auto flex-shrink-0 text-amber-400/70 transition-colors hover:text-amber-200"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
