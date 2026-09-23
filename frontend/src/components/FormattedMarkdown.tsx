"use client";

import React from "react";

interface FormattedMarkdownProps {
  content: string;
  className?: string;
  isDark?: boolean;
}

/**
 * Format inline markdown tokens: **bold**, *italic*, `code`, and [links](url).
 */
export function formatInlineText(text: string, isDark: boolean = true): React.ReactNode {
  if (!text) return null;

  // Regex to capture bold (**text**), code (`text`), italic (*text*), and markdown links ([text](url))
  const tokenRegex = /(\*\*[^*]+?\*\*|`[^`]+?`|(?<!\*)\*[^*]+?\*(?!\*)|\[[^\]]+?\]\([^)]+?\))/g;
  const parts = text.split(tokenRegex);

  return parts.map((part, index) => {
    if (!part) return null;

    // 1. Bold (**text**)
    if (part.startsWith("**") && part.endsWith("**") && part.length >= 4) {
      const boldText = part.slice(2, -2);
      return (
        <strong key={index} className={`font-extrabold ${isDark ? "text-white" : "text-slate-900"}`}>
          {boldText}
        </strong>
      );
    }

    // 2. Inline Code (`code`)
    if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
      const codeText = part.slice(1, -1);
      return (
        <code
          key={index}
          className={`font-mono text-[11px] px-1.5 py-0.5 rounded ${
            isDark ? "bg-white/10 text-[#00ff88] border border-white/10" : "bg-slate-100 text-indigo-700 border border-slate-200"
          }`}
        >
          {codeText}
        </code>
      );
    }

    // 3. Italic (*text*)
    if (part.startsWith("*") && part.endsWith("*") && part.length >= 2) {
      const italicText = part.slice(1, -1);
      return (
        <em key={index} className="italic opacity-90">
          {italicText}
        </em>
      );
    }

    // 4. Markdown Link ([label](url))
    const linkMatch = part.match(/^\[(.*?)\]\((.*?)\)$/);
    if (linkMatch) {
      const [, label, url] = linkMatch;
      return (
        <a
          key={index}
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#38bdf8] hover:underline font-semibold"
        >
          {label}
        </a>
      );
    }

    // Regular Plain Text
    return <React.Fragment key={index}>{part}</React.Fragment>;
  });
}

/**
 * Lightweight, high-performance Markdown parser for AI responses.
 * Parses headings, bullet lists, numbered lists, blockquotes, and inline formatting.
 */
export default function FormattedMarkdown({
  content,
  className = "",
  isDark = true,
}: FormattedMarkdownProps) {
  if (!content) return null;

  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let currentList: { type: "ul" | "ol"; items: string[] } | null = null;

  const flushList = () => {
    if (!currentList) return;
    const ListTag = currentList.type;
    const listKey = `list-${elements.length}`;

    elements.push(
      <ListTag
        key={listKey}
        className={`my-2 space-y-1.5 pl-5 ${
          currentList.type === "ul" ? "list-disc marker:text-[#00ff88]" : "list-decimal marker:text-indigo-400"
        } ${isDark ? "text-slate-200" : "text-slate-700"}`}
      >
        {currentList.items.map((item, idx) => (
          <li key={idx} className="leading-relaxed">
            {formatInlineText(item, isDark)}
          </li>
        ))}
      </ListTag>
    );
    currentList = null;
  };

  lines.forEach((line, lineIndex) => {
    const trimmed = line.trim();

    // Empty lines trigger list flushing and paragraph breaks
    if (!trimmed) {
      flushList();
      elements.push(<div key={`spacer-${lineIndex}`} className="h-2" />);
      return;
    }

    // 1. Headings (### H3, ## H2, # H1)
    if (trimmed.startsWith("### ")) {
      flushList();
      elements.push(
        <h4 key={`h3-${lineIndex}`} className={`font-black font-heading text-sm mt-3 mb-1.5 ${isDark ? "text-white" : "text-slate-900"}`}>
          {formatInlineText(trimmed.replace(/^###\s+/, ""), isDark)}
        </h4>
      );
      return;
    }

    if (trimmed.startsWith("## ")) {
      flushList();
      elements.push(
        <h3 key={`h2-${lineIndex}`} className={`font-black font-heading text-base mt-4 mb-2 ${isDark ? "text-white" : "text-slate-900"}`}>
          {formatInlineText(trimmed.replace(/^##\s+/, ""), isDark)}
        </h3>
      );
      return;
    }

    if (trimmed.startsWith("# ")) {
      flushList();
      elements.push(
        <h2 key={`h1-${lineIndex}`} className={`font-black font-heading text-lg mt-5 mb-2.5 ${isDark ? "text-white" : "text-slate-900"}`}>
          {formatInlineText(trimmed.replace(/^#\s+/, ""), isDark)}
        </h2>
      );
      return;
    }

    // 2. Unordered Bullet Lists (•, -, *)
    const bulletMatch = line.match(/^(\s*)([•\-\*])\s+(.*)$/);
    if (bulletMatch) {
      const itemContent = bulletMatch[3];
      if (!currentList || currentList.type !== "ul") {
        flushList();
        currentList = { type: "ul", items: [] };
      }
      currentList.items.push(itemContent);
      return;
    }

    // 3. Ordered Lists (1., 2., 3.)
    const numberMatch = line.match(/^(\s*)(\d+)\.\s+(.*)$/);
    if (numberMatch) {
      const itemContent = numberMatch[3];
      if (!currentList || currentList.type !== "ol") {
        flushList();
        currentList = { type: "ol", items: [] };
      }
      currentList.items.push(itemContent);
      return;
    }

    // 4. Regular Paragraphs
    flushList();
    elements.push(
      <p key={`p-${lineIndex}`} className={`leading-relaxed my-1 ${isDark ? "text-slate-200" : "text-slate-800"}`}>
        {formatInlineText(line, isDark)}
      </p>
    );
  });

  flushList();

  return <div className={`text-xs space-y-0.5 ${className}`}>{elements}</div>;
}
