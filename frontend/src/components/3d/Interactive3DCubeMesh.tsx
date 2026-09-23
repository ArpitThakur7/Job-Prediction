"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";
import { useApp } from "@/context/AppContext";

export default function Interactive3DCubeMesh() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { currentThemeColors } = useApp();
  const themeRef = useRef(currentThemeColors);

  useEffect(() => {
    themeRef.current = currentThemeColors;
  }, [currentThemeColors]);

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const width = container.clientWidth || 280;
    const height = container.clientHeight || 280;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.set(0, 0, 4.5);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    const ambLight = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 1.5);
    dirLight.position.set(5, 5, 5);
    scene.add(dirLight);

    const meshGeo = new THREE.OctahedronGeometry(1.2, 0);
    const meshMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(themeRef.current.primary),
      roughness: 0.15,
      metalness: 0.85,
    });
    const mesh = new THREE.Mesh(meshGeo, meshMat);
    scene.add(mesh);

    const wireGeo = new THREE.OctahedronGeometry(1.25, 0);
    const wireMat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(themeRef.current.secondary),
      wireframe: true,
      transparent: true,
      opacity: 0.4,
    });
    const wireMesh = new THREE.Mesh(wireGeo, wireMat);
    scene.add(wireMesh);

    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener("resize", handleResize);

    let animId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      const time = clock.getElapsedTime();
      meshMat.color = new THREE.Color(themeRef.current.primary);
      wireMat.color = new THREE.Color(themeRef.current.secondary);

      mesh.rotation.x = time * 0.6;
      mesh.rotation.y = time * 0.8;
      wireMesh.rotation.x = time * 0.6;
      wireMesh.rotation.y = time * 0.8;

      mesh.position.y = Math.sin(time * 2) * 0.1;
      wireMesh.position.y = Math.sin(time * 2) * 0.1;

      renderer.render(scene, camera);
      animId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", handleResize);
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  return (
    <div className="relative w-full h-[240px] rounded-2xl overflow-hidden bg-gradient-to-b from-white/90 to-slate-100/90 border border-slate-200/80 shadow-md backdrop-blur-md">
      <div ref={containerRef} className="w-full h-full" />
    </div>
  );
}
