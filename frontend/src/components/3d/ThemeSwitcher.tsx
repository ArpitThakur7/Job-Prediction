"use client";

import React from "react";
import { useApp, ThemeType } from "@/context/AppContext";

export default function ThemeSwitcher() {
  const { theme, setTheme } = useApp();

  const themes: { id: ThemeType; name: string; icon: string; color: string }[] = [
    { id: "luminary", name: "Luminary", icon: "☀️", color: "from-[#2563eb] to-[#10b981]" },
    { id: "emerald", name: "Emerald", icon: "💎", color: "from-[#059669] to-[#0284c7]" },
    { id: "quantum", name: "Quantum", icon: "🌌", color: "from-[#818cf8] to-[#00ff88]" },
    { id: "cyberpunk", name: "Cyberpunk", icon: "⚡", color: "from-[#00f3ff] to-[#ff007f]" },
    { id: "aurora", name: "Aurora", icon: "✨", color: "from-[#38bdf8] to-[#10b981]" },
    { id: "gold", name: "Gold", icon: "👑", color: "from-[#fbbf24] to-[#f59e0b]" },
  ];

  return (
    <div className="flex items-center gap-1 bg-[#0d1121]/80 backdrop-blur-xl p-1 rounded-full border border-white/10 shadow-lg">
      {themes.map((t) => {
        const isActive = theme === t.id;
        return (
          <button
            key={t.id}
            onClick={() => setTheme(t.id)}
            title={`Switch to ${t.name} Theme`}
            className={`flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1 rounded-full text-[10px] font-mono font-bold transition-all cursor-pointer touch-manipulation select-none ${
              isActive
                ? `bg-gradient-to-r ${t.color} text-black shadow-[0_0_12px_rgba(255,255,255,0.4)] scale-105`
                : "text-[#8b8fa8] hover:text-white hover:bg-white/5"
            }`}
          >
            <span>{t.icon}</span>
            <span className="hidden md:inline">{t.name}</span>
          </button>
        );
      })}
    </div>
  );
}
