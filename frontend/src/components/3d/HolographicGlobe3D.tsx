"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";

interface HolographicGlobe3DProps {
  scoreValue?: number;
  skills?: string[];
  size?: number;
}

export default function HolographicGlobe3D({
  scoreValue = 94,
  skills = ["FastAPI", "React", "Python", "SQL"],
  size = 300,
}: HolographicGlobe3DProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const scene = new THREE.Scene();

    const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
    camera.position.z = 240;

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: "high-performance",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(size, size);
    container.appendChild(renderer.domElement);

    const globeGroup = new THREE.Group();

    // 1. Outer Holographic Wireframe Globe
    const globeGeo = new THREE.SphereGeometry(75, 24, 24);
    const globeMat = new THREE.MeshBasicMaterial({
      color: 0x6c63ff,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    });
    const globeMesh = new THREE.Mesh(globeGeo, globeMat);
    globeGroup.add(globeMesh);

    // 2. Inner Glowing Core
    const coreGeo = new THREE.SphereGeometry(45, 32, 32);
    const coreMat = new THREE.MeshBasicMaterial({
      color: 0x00ff88,
      transparent: true,
      opacity: 0.15,
      wireframe: false,
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    globeGroup.add(coreMesh);

    // Inner wireframe core for depth
    const coreWireGeo = new THREE.IcosahedronGeometry(46, 2);
    const coreWireMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      wireframe: true,
      transparent: true,
      opacity: 0.3,
    });
    const coreWireMesh = new THREE.Mesh(coreWireGeo, coreWireMat);
    globeGroup.add(coreWireMesh);

    // 3. Orbital Particle Ring
    const particleCount = 120;
    const ringGeo = new THREE.BufferGeometry();
    const ringPos = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
      const angle = (i / particleCount) * Math.PI * 2;
      const radius = 98 + (Math.random() - 0.5) * 8;
      ringPos[i * 3] = Math.cos(angle) * radius;
      ringPos[i * 3 + 1] = (Math.random() - 0.5) * 12;
      ringPos[i * 3 + 2] = Math.sin(angle) * radius;
    }

    ringGeo.setAttribute("position", new THREE.BufferAttribute(ringPos, 3));
    const ringMat = new THREE.PointsMaterial({
      color: 0x00ff88,
      size: 3,
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
    });
    const particleRing = new THREE.Points(ringGeo, ringMat);
    particleRing.rotation.x = Math.PI * 0.15;
    globeGroup.add(particleRing);

    // 4. Second Diagonal Ring
    const ringGeo2 = new THREE.BufferGeometry();
    const ringPos2 = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
      const angle = (i / particleCount) * Math.PI * 2;
      const radius = 105;
      ringPos2[i * 3] = Math.cos(angle) * radius;
      ringPos2[i * 3 + 1] = Math.sin(angle) * radius * 0.4;
      ringPos2[i * 3 + 2] = Math.sin(angle) * radius;
    }

    ringGeo2.setAttribute("position", new THREE.BufferAttribute(ringPos2, 3));
    const ringMat2 = new THREE.PointsMaterial({
      color: 0x6c63ff,
      size: 2.5,
      transparent: true,
      opacity: 0.7,
      blending: THREE.AdditiveBlending,
    });
    const particleRing2 = new THREE.Points(ringGeo2, ringMat2);
    particleRing2.rotation.z = Math.PI * 0.25;
    globeGroup.add(particleRing2);

    scene.add(globeGroup);

    // Interactive Dragging / Rotating with Mouse
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };

    const onMouseDown = (e: MouseEvent) => {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const deltaX = e.clientX - previousMousePosition.x;
      const deltaY = e.clientY - previousMousePosition.y;

      globeGroup.rotation.y += deltaX * 0.008;
      globeGroup.rotation.x += deltaY * 0.008;

      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    container.addEventListener("mousedown", onMouseDown);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);

    // Animation loop
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      const elapsedTime = clock.getElapsedTime();

      if (!isDragging) {
        globeGroup.rotation.y += 0.005;
        globeGroup.rotation.x = Math.sin(elapsedTime * 0.5) * 0.1;
      }

      particleRing.rotation.y = elapsedTime * 0.3;
      particleRing2.rotation.y = -elapsedTime * 0.2;

      // Pulse core scale
      const pulseScale = 1 + Math.sin(elapsedTime * 2) * 0.05;
      coreMesh.scale.set(pulseScale, pulseScale, pulseScale);

      renderer.render(scene, camera);
      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      container.removeEventListener("mousedown", onMouseDown);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      globeGeo.dispose();
      globeMat.dispose();
      coreGeo.dispose();
      coreMat.dispose();
      coreWireGeo.dispose();
      coreWireMat.dispose();
      ringGeo.dispose();
      ringMat.dispose();
      ringGeo2.dispose();
      ringMat2.dispose();
      renderer.dispose();
    };
  }, [size]);

  return (
    <div className="relative flex items-center justify-center">
      {/* 3D WebGL Canvas */}
      <div
        ref={containerRef}
        className="cursor-grab active:cursor-grabbing"
        title="Click and drag to rotate the 3D Holographic Globe!"
      />

      {/* Holographic Match Score Overlay inside the 3D Orb */}
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center">
        <span className="text-[11px] font-bold tracking-widest text-[#00ff88] uppercase font-mono bg-[#00ff88]/10 px-2.5 py-0.5 rounded-full border border-[#00ff88]/30 mb-1 backdrop-blur-md animate-pulse">
          ⚡ Match Index
        </span>
        <h2 className="text-4xl font-black font-mono tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-[#a39eff] to-[#00ff88]">
          {scoreValue}%
        </h2>
        <span className="text-[10px] text-[#8b8fa8] font-mono mt-0.5">
          Quantum Skill Fit
        </span>
      </div>

      {/* Floating Orbital Skill Badges around the 3D Globe */}
      <div className="absolute inset-0 pointer-events-none">
        {skills.map((skill, index) => {
          const orbitClass = `orbit-chip-${(index % 4) + 1}`;
          const positions = [
            "top-2 left-2",
            "top-4 right-2",
            "bottom-6 left-4",
            "bottom-4 right-4",
          ];
          return (
            <div
              key={skill}
              className={`absolute ${positions[index % positions.length]} ${orbitClass}`}
            >
              <div className="flex items-center gap-1.5 bg-[#0d1121]/80 backdrop-blur-md border border-[#6c63ff]/40 px-3 py-1 rounded-full shadow-[0_0_15px_rgba(108,99,255,0.2)] text-xs font-mono font-semibold text-white">
                <span className="w-2 h-2 rounded-full bg-[#00ff88] animate-ping" />
                {skill}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
