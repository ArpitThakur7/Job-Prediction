"use client";

import React, { useRef, useState } from "react";

interface Card3DTiltProps {
  children: React.ReactNode;
  className?: string;
  maxDegree?: number;
  scaleOnHover?: number;
  glowColor?: string;
  onClick?: () => void;
}

export default function Card3DTilt({
  children,
  className = "",
  maxDegree = 10,
  scaleOnHover = 1.02,
  glowColor = "rgba(108, 99, 255, 0.25)",
  onClick,
}: Card3DTiltProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [style, setStyle] = useState<React.CSSProperties>({
    transform: "perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)",
    transition: "transform 0.5s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.5s ease",
  });
  const [glarePosition, setGlarePosition] = useState({ x: 50, y: 50, opacity: 0 });

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;

    // Calculate normalized mouse offset (-0.5 to 0.5)
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const px = (mouseX / width) - 0.5;
    const py = (mouseY / height) - 0.5;

    // Calculate rotation angles
    const rotateY = px * maxDegree * 2;
    const rotateX = -py * maxDegree * 2;

    setStyle({
      transform: `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) scale3d(${scaleOnHover}, ${scaleOnHover}, ${scaleOnHover})`,
      boxShadow: `0 20px 40px -10px ${glowColor}, 0 0 20px 0 ${glowColor}`,
      transition: "transform 0.1s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.2s ease",
    });

    setGlarePosition({
      x: (mouseX / width) * 100,
      y: (mouseY / height) * 100,
      opacity: 0.15,
    });
  };

  const handleMouseLeave = () => {
    setStyle({
      transform: "perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)",
      boxShadow: "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
      transition: "transform 0.5s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.5s ease",
    });
    setGlarePosition((prev) => ({ ...prev, opacity: 0 }));
  };

  return (
    <div
      ref={cardRef}
      onClick={onClick}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={style}
      className={`relative overflow-hidden cursor-pointer transform-gpu ${className}`}
    >
      {/* Dynamic Specular Glare Overlay */}
      <div
        className="pointer-events-none absolute inset-0 rounded-2xl transition-opacity duration-300 z-10"
        style={{
          background: `radial-gradient(circle at ${glarePosition.x}% ${glarePosition.y}%, rgba(255, 255, 255, 0.4) 0%, transparent 60%)`,
          opacity: glarePosition.opacity,
        }}
      />
      {children}
    </div>
  );
}
