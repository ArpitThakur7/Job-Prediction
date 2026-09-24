"use client";

import React from "react";
import { motion } from "framer-motion";

interface ScoreOrbProps {
  score: number;
  size?: number;
  label?: string;
  sublabel?: string;
}

export const ScoreOrb3D: React.FC<ScoreOrbProps> = ({
  score,
  size = 72,
  label = "SCORE",
  sublabel,
}) => {
  const radius = (size - 10) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  const getColor = (s: number) => {
    if (s >= 80) return { stroke: "#10b981", glow: "rgba(16, 185, 129, 0.4)", text: "#10b981" };
    if (s >= 65) return { stroke: "#00f3ff", glow: "rgba(0, 243, 255, 0.4)", text: "#00f3ff" };
    return { stroke: "#f59e0b", glow: "rgba(245, 158, 11, 0.4)", text: "#f59e0b" };
  };

  const { stroke, glow, text } = getColor(score);

  return (
    <div className="relative flex flex-col items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="rgba(255, 255, 255, 0.08)"
          strokeWidth="6"
          fill="transparent"
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={stroke}
          strokeWidth="6"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset }}
          transition={{ duration: 1.2, ease: "easeOut" }}
          strokeLinecap="round"
          fill="transparent"
          style={{ filter: `drop-shadow(0 0 6px ${glow})` }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <span className="font-mono font-black text-sm tracking-tight" style={{ color: text }}>
          {score}
        </span>
        {label && (
          <span className="text-[8px] font-mono uppercase tracking-wider text-slate-400 opacity-80">
            {label}
          </span>
        )}
      </div>
      {sublabel && (
        <span className="mt-1 text-[9px] font-mono text-slate-400 text-center">{sublabel}</span>
      )}
    </div>
  );
};

export default ScoreOrb3D;
