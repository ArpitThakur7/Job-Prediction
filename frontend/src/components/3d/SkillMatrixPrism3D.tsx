"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";

interface SkillMatrixPrism3DProps {
  score?: number;
  skills?: string[];
  size?: number;
}

export default function SkillMatrixPrism3D({
  score = 92,
  skills = ["FastAPI", "React", "Python", "SQL", "Docker", "PyTorch"],
  size = 280,
}: SkillMatrixPrism3DProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const scene = new THREE.Scene();

    const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
    camera.position.z = 220;

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: "high-performance",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(size, size);
    container.appendChild(renderer.domElement);

    const prismGroup = new THREE.Group();

    // 1. Center Crystal Octahedron / Prism
    const octaGeo = new THREE.OctahedronGeometry(55, 0);
    const octaMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      wireframe: true,
      transparent: true,
      opacity: 0.5,
    });
    const octaMesh = new THREE.Mesh(octaGeo, octaMat);
    prismGroup.add(octaMesh);

    // Inner Glowing Core Pyramid
    const innerGeo = new THREE.ConeGeometry(32, 60, 4);
    const innerMat = new THREE.MeshBasicMaterial({
      color: 0x00ff88,
      wireframe: false,
      transparent: true,
      opacity: 0.25,
    });
    const innerMesh = new THREE.Mesh(innerGeo, innerMat);
    innerMesh.rotation.x = Math.PI;
    prismGroup.add(innerMesh);

    // 2. Orbital Constellation Ring
    const nodeCount = Math.min(skills.length, 8);
    const nodeGroup = new THREE.Group();

    for (let i = 0; i < nodeCount; i++) {
      const angle = (i / nodeCount) * Math.PI * 2;
      const radius = 85;
      const x = Math.cos(angle) * radius;
      const y = (Math.sin(angle * 2) * 15);
      const z = Math.sin(angle) * radius;

      // Small glowing node sphere
      const nodeGeo = new THREE.SphereGeometry(6, 12, 12);
      const nodeMat = new THREE.MeshBasicMaterial({
        color: i % 2 === 0 ? 0x00ff88 : 0x6c63ff,
      });
      const nodeMesh = new THREE.Mesh(nodeGeo, nodeMat);
      nodeMesh.position.set(x, y, z);
      nodeGroup.add(nodeMesh);

      // Connecting line beam to center prism
      const lineGeo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(x, y, z),
      ]);
      const lineMat = new THREE.LineBasicMaterial({
        color: 0x38bdf8,
        transparent: true,
        opacity: 0.35,
      });
      const lineMesh = new THREE.Line(lineGeo, lineMat);
      nodeGroup.add(lineMesh);
    }

    prismGroup.add(nodeGroup);
    scene.add(prismGroup);

    // Interactive Drag Rotation
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

      prismGroup.rotation.y += deltaX * 0.008;
      prismGroup.rotation.x += deltaY * 0.008;

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
        prismGroup.rotation.y = elapsedTime * 0.4;
        prismGroup.rotation.x = Math.sin(elapsedTime * 0.6) * 0.15;
      }

      nodeGroup.rotation.y = -elapsedTime * 0.2;
      innerMesh.rotation.y = elapsedTime * 0.5;

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
      octaGeo.dispose();
      octaMat.dispose();
      innerGeo.dispose();
      innerMat.dispose();
      renderer.dispose();
    };
  }, [size, skills]);

  return (
    <div className="relative flex flex-col items-center justify-center">
      <div
        ref={containerRef}
        className="cursor-grab active:cursor-grabbing"
        title="Click & drag to rotate the 3D Skill Prism!"
      />

      {/* Holographic score overlay */}
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center">
        <span className="text-[10px] font-bold tracking-widest text-[#38bdf8] uppercase font-mono bg-[#38bdf8]/10 px-2.5 py-0.5 rounded-full border border-[#38bdf8]/30 mb-1 backdrop-blur-md">
          ⚡ Skill Affinity
        </span>
        <h3 className="text-3xl font-black font-mono tracking-tight text-white drop-shadow-[0_0_15px_rgba(56,189,248,0.5)]">
          {score}%
        </h3>
      </div>
    </div>
  );
}
