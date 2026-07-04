import React from "react";

/**
 * 依存を増やさない軽量Markdownレンダラ（ルール本文用のサブセット）。
 * 対応: 見出し(#/##/###)、箇条書き(-,*)、番号付き(1.)、太字(**)、段落、改行。
 * これ以上リッチにしたくなったら react-markdown 等へ差し替えるのが拡張ポイント。
 */

/** インライン **太字** を <strong> に変換。 */
function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    const m = /^\*\*([^*]+)\*\*$/.exec(part);
    if (m) return <strong key={`${keyPrefix}-b${i}`} className="font-semibold text-white">{m[1]}</strong>;
    return <React.Fragment key={`${keyPrefix}-t${i}`}>{part}</React.Fragment>;
  });
}

export function SimpleMarkdown({ source, className = "" }: { source: string; className?: string }) {
  const lines = (source ?? "").replace(/\r\n/g, "\n").split("\n");
  const blocks: React.ReactNode[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  let para: string[] = [];

  const flushList = () => {
    if (!list) return;
    const items = list.items.map((it, i) => (
      <li key={`li-${blocks.length}-${i}`} className="text-slate-300">{renderInline(it, `li-${blocks.length}-${i}`)}</li>
    ));
    blocks.push(
      list.ordered ? (
        <ol key={`ol-${blocks.length}`} className="ml-5 list-decimal space-y-1 text-sm leading-relaxed">{items}</ol>
      ) : (
        <ul key={`ul-${blocks.length}`} className="ml-5 list-disc space-y-1 text-sm leading-relaxed marker:text-brand-400">{items}</ul>
      ),
    );
    list = null;
  };

  const flushPara = () => {
    if (para.length === 0) return;
    const text = para.join("\n");
    blocks.push(
      <p key={`p-${blocks.length}`} className="whitespace-pre-wrap text-sm leading-relaxed text-slate-300">
        {renderInline(text, `p-${blocks.length}`)}
      </p>,
    );
    para = [];
  };

  for (const raw of lines) {
    const line = raw.trimEnd();

    if (line.trim() === "") {
      flushPara();
      flushList();
      continue;
    }

    const heading = /^(#{1,3})\s+(.*)$/.exec(line);
    if (heading) {
      flushPara();
      flushList();
      const level = heading[1].length;
      const cls = level === 1 ? "text-base font-bold text-white" : level === 2 ? "text-sm font-bold text-white" : "text-sm font-semibold text-slate-200";
      blocks.push(<p key={`h-${blocks.length}`} className={`mt-2 ${cls}`}>{renderInline(heading[2], `h-${blocks.length}`)}</p>);
      continue;
    }

    const ul = /^[-*]\s+(.*)$/.exec(line);
    if (ul) {
      flushPara();
      if (!list || list.ordered) { flushList(); list = { ordered: false, items: [] }; }
      list.items.push(ul[1]);
      continue;
    }

    const ol = /^\d+\.\s+(.*)$/.exec(line);
    if (ol) {
      flushPara();
      if (!list || !list.ordered) { flushList(); list = { ordered: true, items: [] }; }
      list.items.push(ol[1]);
      continue;
    }

    flushList();
    para.push(line);
  }
  flushPara();
  flushList();

  return <div className={`space-y-3 ${className}`}>{blocks}</div>;
}
