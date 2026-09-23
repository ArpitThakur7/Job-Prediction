"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";
import { useApp } from "@/context/AppContext";

export default function Hero3DWorkspace() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { currentThemeColors } = useApp();
  const themeRef = useRef(currentThemeColors);

  useEffect(() => {
    themeRef.current = currentThemeColors;
  }, [currentThemeColors]);

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const width = container.clientWidth || 480;
    const height = container.clientHeight || 480;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 1.2, 6.5);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // 1. Lighting Setup
    const ambLight = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 1.8);
    dirLight.position.set(10, 15, 8);
    scene.add(dirLight);

    const pointLight = new THREE.PointLight(themeRef.current.primary, 1.5, 100);
    pointLight.position.set(-5, 2, 3);
    scene.add(pointLight);

    // 2. Central 3D Icosahedron Quantum Core
    const coreGroup = new THREE.Group();
    const coreGeo = new THREE.IcosahedronGeometry(1.1, 0);
    const coreMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(themeRef.current.primary),
      roughness: 0.15,
      metalness: 0.85,
      wireframe: false,
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    coreGroup.add(coreMesh);

    // Wireframe Overlay
    const wireGeo = new THREE.IcosahedronGeometry(1.15, 0);
    const wireMat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(themeRef.current.secondary),
      wireframe: true,
      transparent: true,
      opacity: 0.4,
    });
    const wireMesh = new THREE.Mesh(wireGeo, wireMat);
    coreGroup.add(wireMesh);

    // 3. Orbital Rings
    const ring1Geo = new THREE.TorusGeometry(1.8, 0.03, 16, 100);
    const ring1Mat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(themeRef.current.secondary),
      roughness: 0.2,
      metalness: 0.9,
      emissive: new THREE.Color(themeRef.current.secondary),
      emissiveIntensity: 0.4,
    });
    const ring1 = new THREE.Mesh(ring1Geo, ring1Mat);
    ring1.rotation.x = Math.PI / 3;
    coreGroup.add(ring1);

    const ring2Geo = new THREE.TorusGeometry(2.3, 0.02, 16, 100);
    const ring2Mat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(themeRef.current.primary),
      roughness: 0.2,
      metalness: 0.9,
      emissive: new THREE.Color(themeRef.current.primary),
      emissiveIntensity: 0.3,
    });
    const ring2 = new THREE.Mesh(ring2Geo, ring2Mat);
    ring2.rotation.x = -Math.PI / 4;
    ring2.rotation.y = Math.PI / 4;
    coreGroup.add(ring2);

    // 4. Base Platform
    const baseGeo = new THREE.CylinderGeometry(3, 3.2, 0.1, 64);
    const baseMat = new THREE.MeshStandardMaterial({
      color: 0xf1f5f9,
      roughness: 0.3,
      metalness: 0.2,
    });
    const baseMesh = new THREE.Mesh(baseGeo, baseMat);
    baseMesh.position.y = -2.2;
    coreGroup.add(baseMesh);

    scene.add(coreGroup);

    // 5. Floating Sparkles
    const particleCount = 80;
    const particleGeo = new THREE.BufferGeometry();
    const posArr = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
      posArr[i * 3] = (Math.random() - 0.5) * 8;
      posArr[i * 3 + 1] = (Math.random() - 0.5) * 6;
      posArr[i * 3 + 2] = (Math.random() - 0.5) * 6;
    }

    particleGeo.setAttribute("position", new THREE.BufferAttribute(posArr, 3));
    const particleMat = new THREE.PointsMaterial({
      size: 0.08,
      color: new THREE.Color(themeRef.current.primary),
      transparent: true,
      opacity: 0.6,
    });
    const particleSystem = new THREE.Points(particleGeo, particleMat);
    scene.add(particleSystem);

    // Mouse Drag & Rotation
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

      coreGroup.rotation.y += deltaX * 0.008;
      coreGroup.rotation.x += deltaY * 0.008;

      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    container.addEventListener("mousedown", onMouseDown);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);

    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener("resize", handleResize);

    // Animation Loop
    let animId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      const time = clock.getElapsedTime();

      // Color Theme Update
      const pColor = new THREE.Color(themeRef.current.primary);
      const sColor = new THREE.Color(themeRef.current.secondary);
      coreMat.color = pColor;
      wireMat.color = sColor;
      ring1Mat.color = sColor;
      ring2Mat.color = pColor;
      pointLight.color = pColor;

      coreMesh.rotation.y = time * 0.5;
      wireMesh.rotation.x = time * 0.3;
      ring1.rotation.z = time * 0.6;
      ring2.rotation.y = time * 0.4;
      coreGroup.position.y = Math.sin(time * 1.5) * 0.15;

      particleSystem.rotation.y = time * 0.05;

      renderer.render(scene, camera);
      animId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animId);
      container.removeEventListener("mousedown", onMouseDown);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
      window.removeEventListener("resize", handleResize);
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  return (
    <div className="relative w-full h-[480px] rounded-3xl overflow-hidden bg-gradient-to-b from-slate-50/80 via-white/50 to-slate-100/90 border border-slate-200/80 shadow-2xl backdrop-blur-xl">
      <div ref={containerRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Floating HTML Badges */}
      <div className="absolute top-6 left-6 pointer-events-none">
        <div className="flex items-center gap-1.5 px-3 py-1 bg-white/90 backdrop-blur-md rounded-full shadow-lg border border-emerald-300 text-emerald-800 text-[11px] font-extrabold select-none">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          ML Match 98.4%
        </div>
      </div>

      <div className="absolute top-16 right-6 pointer-events-none">
        <div className="flex items-center gap-1.5 px-3 py-1 bg-white/90 backdrop-blur-md rounded-full shadow-lg border border-sky-300 text-sky-800 text-[11px] font-extrabold select-none">
          <span className="w-2 h-2 rounded-full bg-sky-500 animate-ping" />
          Pinecone RAG Vector
        </div>
      </div>

      <div className="absolute bottom-6 left-6 pointer-events-none">
        <div className="flex items-center gap-1.5 px-3 py-1 bg-white/90 backdrop-blur-md rounded-full shadow-lg border border-indigo-300 text-indigo-800 text-[11px] font-extrabold select-none">
          <span className="w-2 h-2 rounded-full bg-indigo-500" />
          54,933 Resumes Ingested
        </div>
      </div>

      <div className="absolute top-0 inset-x-0 h-12 bg-gradient-to-b from-white to-transparent pointer-events-none" />
    </div>
  );
}
