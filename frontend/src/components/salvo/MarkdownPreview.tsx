"use client";

import React, { useMemo } from "react";

interface MarkdownPreviewProps {
  content: string;
  className?: string;
}

export default function MarkdownPreview({ content, className = "" }: MarkdownPreviewProps) {
  const renderedElements = useMemo(() => {
    if (!content.trim()) {
      return (
        <div className="py-12 text-center text-xs font-mono text-slate-500 italic">
          No markdown content entered yet. Start typing on the left.
        </div>
      );
    }

    const lines = content.split("\n");
    const elements: React.ReactNode[] = [];
    let inCodeBlock = false;
    let codeBlockContent: string[] = [];
    let codeBlockLang = "";
    let inList = false;
    let listItems: React.ReactNode[] = [];

    const flushList = (key: string) => {
      if (inList && listItems.length > 0) {
        elements.push(
          <ul key={key} className="space-y-1.5 my-3 pl-5 list-disc marker:text-cyan-400 text-xs text-slate-300">
            {listItems}
          </ul>
        );
        listItems = [];
        inList = false;
      }
    };

    const parseInline = (text: string): React.ReactNode => {
      // Inline parser for bold, italics, inline code, and links
      const parts: React.ReactNode[] = [];
      let remaining = text;
      let partKey = 0;

      while (remaining.length > 0) {
        // Code
        const codeMatch = remaining.match(/`([^`]+)`/);
        // Bold
        const boldMatch = remaining.match(/\*\*([^*]+)\*\*/);
        // Italic
        const italicMatch = remaining.match(/\*([^*]+)\*/);
        // Link
        const linkMatch = remaining.match(/\[([^\]]+)\]\(([^)]+)\)/);

        // Find the earliest match
        const matches = [
          codeMatch ? { type: "code", match: codeMatch, index: codeMatch.index! } : null,
          boldMatch ? { type: "bold", match: boldMatch, index: boldMatch.index! } : null,
          italicMatch ? { type: "italic", match: italicMatch, index: italicMatch.index! } : null,
          linkMatch ? { type: "link", match: linkMatch, index: linkMatch.index! } : null,
        ]
          .filter(Boolean)
          .sort((a, b) => a!.index - b!.index);

        if (matches.length === 0) {
          parts.push(<span key={partKey++}>{remaining}</span>);
          break;
        }

        const earliest = matches[0]!;
        if (earliest.index > 0) {
          parts.push(<span key={partKey++}>{remaining.slice(0, earliest.index)}</span>);
        }

        if (earliest.type === "code") {
          parts.push(
            <code key={partKey++} className="px-1.5 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/20 text-cyan-300 font-mono text-[11px]">
              {earliest.match[1]}
            </code>
          );
        } else if (earliest.type === "bold") {
          parts.push(
            <strong key={partKey++} className="font-bold text-white">
              {earliest.match[1]}
            </strong>
          );
        } else if (earliest.type === "italic") {
          parts.push(
            <em key={partKey++} className="italic text-slate-300">
              {earliest.match[1]}
            </em>
          );
        } else if (earliest.type === "link") {
          parts.push(
            <a
              key={partKey++}
              href={earliest.match[2]}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan-400 hover:text-cyan-300 underline underline-offset-2"
            >
              {earliest.match[1]}
            </a>
          );
        }

        remaining = remaining.slice(earliest.index + earliest.match[0].length);
      }

      return parts;
    };

    lines.forEach((line, idx) => {
      // Code blocks
      if (line.startsWith("```")) {
        if (inCodeBlock) {
          flushList(`list-before-code-${idx}`);
          elements.push(
            <div key={`code-${idx}`} className="my-4 rounded-xl border border-white/10 bg-black/60 overflow-hidden font-mono text-xs">
              {codeBlockLang && (
                <div className="px-3 py-1 bg-white/5 border-b border-white/5 text-[10px] text-slate-400 uppercase tracking-wider">
                  {codeBlockLang}
                </div>
              )}
              <pre className="p-4 overflow-x-auto text-slate-300 leading-relaxed">
                <code>{codeBlockContent.join("\n")}</code>
              </pre>
            </div>
          );
          codeBlockContent = [];
          codeBlockLang = "";
          inCodeBlock = false;
        } else {
          flushList(`list-before-code-start-${idx}`);
          inCodeBlock = true;
          codeBlockLang = line.slice(3).trim();
        }
        return;
      }

      if (inCodeBlock) {
        codeBlockContent.push(line);
        return;
      }

      // Headings
      if (line.startsWith("# ")) {
        flushList(`list-before-h1-${idx}`);
        elements.push(
          <div key={`h1-${idx}`} className="mt-6 mb-3 pb-2 border-b border-cyan-500/30">
            <h1 className="text-xl font-black text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
              <span className="w-1.5 h-5 rounded-full bg-cyan-500" />
              {parseInline(line.slice(2))}
            </h1>
          </div>
        );
        return;
      }

      if (line.startsWith("## ")) {
        flushList(`list-before-h2-${idx}`);
        elements.push(
          <div key={`h2-${idx}`} className="mt-5 mb-2.5">
            <h2 className="text-base font-bold text-cyan-700 dark:text-cyan-300 tracking-tight flex items-center gap-2">
              <span className="w-1 h-3.5 rounded-full bg-cyan-500" />
              {parseInline(line.slice(3))}
            </h2>
          </div>
        );
        return;
      }

      if (line.startsWith("### ")) {
        flushList(`list-before-h3-${idx}`);
        elements.push(
          <h3 key={`h3-${idx}`} className="mt-4 mb-2 text-sm font-bold text-slate-800 dark:text-slate-200">
            {parseInline(line.slice(4))}
          </h3>
        );
        return;
      }

      // Blockquotes
      if (line.startsWith("> ")) {
        flushList(`list-before-bq-${idx}`);
        elements.push(
          <blockquote key={`bq-${idx}`} className="my-3 pl-4 border-l-2 border-cyan-500 bg-cyan-50 dark:bg-cyan-950/20 py-2 pr-3 rounded-r-lg text-xs text-cyan-900 dark:text-cyan-200 italic font-mono">
            {parseInline(line.slice(2))}
          </blockquote>
        );
        return;
      }

      // Horizontal rule
      if (line.trim() === "---" || line.trim() === "***") {
        flushList(`list-before-hr-${idx}`);
        elements.push(<hr key={`hr-${idx}`} className="my-6 border-slate-200 dark:border-white/10" />);
        return;
      }

      // Lists
      const listMatch = line.match(/^(\s*)[-*+]\s+(.*)$/);
      if (listMatch) {
        inList = true;
        listItems.push(
          <li key={`li-${idx}`} className="leading-relaxed text-slate-700 dark:text-slate-300">
            {parseInline(listMatch[2])}
          </li>
        );
        return;
      }

      // Ordered list
      const numMatch = line.match(/^(\s*)\d+\.\s+(.*)$/);
      if (numMatch) {
        inList = true;
        listItems.push(
          <li key={`li-${idx}`} className="leading-relaxed text-slate-700 dark:text-slate-300">
            {parseInline(numMatch[2])}
          </li>
        );
        return;
      }

      flushList(`list-before-p-${idx}`);

      // Blank line
      if (!line.trim()) {
        elements.push(<div key={`blank-${idx}`} className="h-2" />);
        return;
      }

      // Regular paragraph
      elements.push(
        <p key={`p-${idx}`} className="my-1.5 text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-sans">
          {parseInline(line)}
        </p>
      );
    });

    flushList("list-end");

    return elements;
  }, [content]);

  return (
    <div className={`markdown-preview font-sans select-text ${className}`}>
      {renderedElements}
    </div>
  );
}
