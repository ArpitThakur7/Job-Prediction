"use client";

import React from "react";
import { motion } from "framer-motion";
import { fitColor } from "@/lib/jobScore";

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

  const stroke = fitColor(score);
  const glow = `${stroke}66`;
  const text = stroke;

  return (
    <div className="relative flex flex-col items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="rgba(128, 128, 160, 0.16)"
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
        <span className="font-display font-extrabold text-base leading-none tabular" style={{ color: text }}>
          {score}
        </span>
        {label && (
          <span className="text-[10px] font-medium opacity-60">
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
