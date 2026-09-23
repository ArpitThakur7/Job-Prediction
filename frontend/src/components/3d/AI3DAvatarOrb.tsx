"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";

interface AI3DAvatarOrbProps {
  isThinking?: boolean;
  size?: number;
}

export default function AI3DAvatarOrb({
  isThinking = false,
  size = 200,
}: AI3DAvatarOrbProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const scene = new THREE.Scene();

    const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
    camera.position.z = 180;

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: "high-performance",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(size, size);
    container.appendChild(renderer.domElement);

    const orbGroup = new THREE.Group();

    // 1. AI Core Icosahedron Wireframe
    const coreGeo = new THREE.IcosahedronGeometry(45, 2);
    const coreMat = new THREE.MeshBasicMaterial({
      color: 0x6c63ff,
      wireframe: true,
      transparent: true,
      opacity: 0.5,
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    orbGroup.add(coreMesh);

    // 2. Inner Glowing Energy Sphere
    const innerGeo = new THREE.SphereGeometry(25, 24, 24);
    const innerMat = new THREE.MeshBasicMaterial({
      color: 0x00ff88,
      transparent: true,
      opacity: 0.4,
    });
    const innerMesh = new THREE.Mesh(innerGeo, innerMat);
    orbGroup.add(innerMesh);

    // 3. Dual Orbital Energy Rings
    const ringCount = 80;
    const ringGeo = new THREE.BufferGeometry();
    const ringPos = new Float32Array(ringCount * 3);

    for (let i = 0; i < ringCount; i++) {
      const angle = (i / ringCount) * Math.PI * 2;
      const radius = 62;
      ringPos[i * 3] = Math.cos(angle) * radius;
      ringPos[i * 3 + 1] = Math.sin(angle) * radius * 0.3;
      ringPos[i * 3 + 2] = Math.sin(angle) * radius;
    }

    ringGeo.setAttribute("position", new THREE.BufferAttribute(ringPos, 3));
    const ringMat = new THREE.PointsMaterial({
      color: 0x38bdf8,
      size: 3,
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
    });
    const ringPoints = new THREE.Points(ringGeo, ringMat);
    ringPoints.rotation.x = Math.PI * 0.2;
    orbGroup.add(ringPoints);

    scene.add(orbGroup);

    // Drag Rotation
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

      orbGroup.rotation.y += deltaX * 0.01;
      orbGroup.rotation.x += deltaY * 0.01;

      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    container.addEventListener("mousedown", onMouseDown);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);

    // Animation Loop
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      const elapsedTime = clock.getElapsedTime();

      if (!isDragging) {
        orbGroup.rotation.y = elapsedTime * (isThinking ? 1.5 : 0.6);
        orbGroup.rotation.x = Math.sin(elapsedTime) * 0.15;
      }

      ringPoints.rotation.z = elapsedTime * (isThinking ? 2.0 : 0.8);

      // Pulse core scale
      const scaleSpeed = isThinking ? 6 : 2;
      const pulseScale = 1 + Math.sin(elapsedTime * scaleSpeed) * (isThinking ? 0.12 : 0.05);
      coreMesh.scale.set(pulseScale, pulseScale, pulseScale);

      // Color transition when thinking
      if (isThinking) {
        coreMat.color.setHex(0x00ff88);
        innerMat.color.setHex(0x38bdf8);
      } else {
        coreMat.color.setHex(0x6c63ff);
        innerMat.color.setHex(0x00ff88);
      }

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
      coreGeo.dispose();
      coreMat.dispose();
      innerGeo.dispose();
      innerMat.dispose();
      ringGeo.dispose();
      ringMat.dispose();
      renderer.dispose();
    };
  }, [size, isThinking]);

  return (
    <div className="relative flex flex-col items-center justify-center">
      <div
        ref={containerRef}
        className="cursor-grab active:cursor-grabbing"
        title="AI Career Assistant 3D Avatar"
      />

      {/* Floating Status Ring */}
      <div className="absolute -bottom-2 flex items-center gap-1.5 bg-[#0d1121]/90 backdrop-blur-md px-3 py-1 rounded-full border border-white/10 text-[10px] font-mono text-white shadow-lg">
        <span
          className={`w-2 h-2 rounded-full ${
            isThinking ? "bg-[#00ff88] animate-ping" : "bg-[#6c63ff]"
          }`}
        />
        <span>{isThinking ? "Thinking..." : "LLaMA 3 AI Ready"}</span>
      </div>
    </div>
  );
}
