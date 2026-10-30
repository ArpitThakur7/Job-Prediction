"use client";

import React, { useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Html, Line, Float } from "@react-three/drei";
import * as THREE from "three";
import { SalvoJob } from "@/lib/salvoClient";
import { fitColor, jobScore } from "@/lib/jobScore";

interface Props {
  jobs: SalvoJob[];
  primary: string;
  onPick?: (job: SalvoJob) => void;
}

type Node = { job: SalvoJob; score: number; pos: THREE.Vector3; size: number };

/**
 * Real jobs from the feed, arranged around the candidate's resume.
 * Distance from the centre encodes fit: the closer a job sits, the better it matches.
 */
function layout(jobs: SalvoJob[]): Node[] {
  const golden = Math.PI * (3 - Math.sqrt(5));
  const n = jobs.length;
  return jobs.map((job, i) => {
    const score = jobScore(job);
    const radius = 1.5 + (1 - score / 100) * 2.6;
    const y = 1 - (i / Math.max(1, n - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    const theta = golden * i;
    const pos = new THREE.Vector3(Math.cos(theta) * r, y * 0.72, Math.sin(theta) * r).multiplyScalar(radius);
    return { job, score, pos, size: 0.07 + (score / 100) * 0.09 };
  });
}

function Scene({ jobs, primary, onPick }: Props) {
  const group = useRef<THREE.Group>(null);
  const [hovered, setHovered] = useState<number | null>(null);
  const nodes = useMemo(() => layout(jobs), [jobs]);
  const top = useMemo(() => [...nodes].sort((a, b) => b.score - a.score).slice(0, 5), [nodes]);
  const still = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  useFrame((_, dt) => {
    if (group.current && !still && hovered === null) group.current.rotation.y += dt * 0.08;
  });

  return (
    <group ref={group}>
      {/* The candidate's resume */}
      <Float speed={still ? 0 : 1.6} floatIntensity={0.4} rotationIntensity={0.2}>
        <mesh>
          <icosahedronGeometry args={[0.62, 4]} />
          <meshPhysicalMaterial
            color={primary}
            roughness={0.12}
            transmission={0.55}
            thickness={1.2}
            clearcoat={1}
            emissive={primary}
            emissiveIntensity={0.35}
          />
        </mesh>
        <Html center distanceFactor={7} style={{ pointerEvents: "none" }}>
          <span className="font-display text-white text-sm font-bold drop-shadow">You</span>
        </Html>
      </Float>

      {top.map((n) => (
        <Line key={n.job.url} points={[[0, 0, 0], n.pos.toArray()]} color={fitColor(n.score)} lineWidth={1.2} transparent opacity={0.45} />
      ))}

      {nodes.map((n, i) => (
        <mesh
          key={n.job.url}
          position={n.pos}
          scale={hovered === i ? 1.7 : 1}
          onPointerOver={(e) => {
            e.stopPropagation();
            setHovered(i);
            document.body.style.cursor = "pointer";
          }}
          onPointerOut={() => {
            setHovered(null);
            document.body.style.cursor = "";
          }}
          onClick={(e) => {
            e.stopPropagation();
            onPick?.(n.job);
          }}
        >
          <sphereGeometry args={[n.size, 24, 24]} />
          <meshPhysicalMaterial color={fitColor(n.score)} roughness={0.2} clearcoat={1} emissive={fitColor(n.score)} emissiveIntensity={hovered === i ? 0.8 : 0.25} />
          {hovered === i && (
            <Html distanceFactor={8} position={[0, n.size + 0.18, 0]} center style={{ pointerEvents: "none" }}>
              <div className="glass-strong rounded-2xl px-3 py-2 w-56 text-left">
                <p className="text-[13px] font-semibold leading-snug line-clamp-2">{n.job.title}</p>
                <p className="text-xs opacity-70 truncate">{n.job.company}</p>
                <p className="text-xs font-bold mt-1 tabular" style={{ color: fitColor(n.score) }}>
                  {n.score}% fit
                </p>
              </div>
            </Html>
          )}
        </mesh>
      ))}
    </group>
  );
}

export default function JobConstellation3D(props: Props) {
  return (
    <Canvas camera={{ position: [0, 1.4, 9.4], fov: 42 }} dpr={[1, 1.75]} gl={{ antialias: true, alpha: true }}>
      <ambientLight intensity={0.9} />
      <directionalLight position={[4, 6, 5]} intensity={1.4} />
      <pointLight position={[-4, -2, -3]} intensity={18} color={props.primary} />
      <Scene {...props} />
    </Canvas>
  );
}
