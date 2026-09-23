"use client";

import React from "react";

interface CyberBorderProps {
  children: React.ReactNode;
  className?: string;
  glowColor?: "purple" | "green" | "cyan" | "gold";
  active?: boolean;
}

export default function CyberBorder({
  children,
  className = "",
  glowColor = "purple",
  active = false,
}: CyberBorderProps) {
  const colorMap = {
    purple: "from-[#6c63ff] via-[#a39eff] to-[#38bdf8]",
    green: "from-[#00ff88] via-[#34d399] to-[#38bdf8]",
    cyan: "from-[#38bdf8] via-[#818cf8] to-[#c084fc]",
    gold: "from-[#fbbf24] via-[#f59e0b] to-[#ec4899]",
  };

  const shadowMap = {
    purple: "shadow-[0_0_25px_rgba(108,99,255,0.25)]",
    green: "shadow-[0_0_25px_rgba(0,255,136,0.25)]",
    cyan: "shadow-[0_0_25px_rgba(56,189,248,0.25)]",
    gold: "shadow-[0_0_25px_rgba(251,191,36,0.25)]",
  };

  return (
    <div className={`relative group p-[1px] rounded-2xl transition-all duration-300 ${shadowMap[glowColor]} ${className}`}>
      {/* Animated Gradient Cyber Rim */}
      <div
        className={`absolute inset-0 rounded-2xl bg-gradient-to-r ${colorMap[glowColor]} opacity-40 group-hover:opacity-100 transition-opacity duration-500 blur-[1px] ${
          active ? "opacity-100 animate-pulse" : ""
        }`}
      />

      {/* Cyber Corner Crosshair Tech Accents */}
      <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-white/80 rounded-tl-2xl pointer-events-none z-20" />
      <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-white/80 rounded-tr-2xl pointer-events-none z-20" />
      <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-white/80 rounded-bl-2xl pointer-events-none z-20" />
      <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-white/80 rounded-br-2xl pointer-events-none z-20" />

      {/* Card Content Container */}
      <div className="relative bg-[#0d1121]/90 backdrop-blur-xl rounded-[15px] h-full z-10">
        {children}
      </div>
    </div>
  );
}
