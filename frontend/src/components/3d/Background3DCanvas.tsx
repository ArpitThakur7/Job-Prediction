"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";
import { useApp } from "@/context/AppContext";

export default function Background3DCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { currentThemeColors } = useApp();

  const themeRef = useRef(currentThemeColors);
  useEffect(() => {
    themeRef.current = currentThemeColors;
  }, [currentThemeColors]);

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const scene = new THREE.Scene();

    scene.fog = new THREE.FogExp2(0x04060d, 0.001);

    const camera = new THREE.PerspectiveCamera(
      60,
      window.innerWidth / window.innerHeight,
      0.1,
      1400
    );
    camera.position.z = 460;

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: "high-performance",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    container.appendChild(renderer.domElement);

    // 1. Gentle Floating Micro-Dust Particles (240 Ambient Particles)
    const particleCount = 240;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const speeds = new Float32Array(particleCount * 3);

    const color1 = new THREE.Color(themeRef.current.primary);
    const color2 = new THREE.Color(themeRef.current.secondary);

    for (let i = 0; i < particleCount; i++) {
      const idx = i * 3;
      positions[idx] = (Math.random() - 0.5) * 1300;
      positions[idx + 1] = (Math.random() - 0.5) * 1100;
      positions[idx + 2] = (Math.random() - 0.5) * 700;

      speeds[idx] = (Math.random() - 0.5) * 0.2;
      speeds[idx + 1] = (Math.random() - 0.5) * 0.2;
      speeds[idx + 2] = (Math.random() - 0.5) * 0.2;

      const mix = Math.random();
      const c = color1.clone().lerp(color2, mix);
      colors[idx] = c.r;
      colors[idx + 1] = c.g;
      colors[idx + 2] = c.b;
    }

    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    const particleMaterial = new THREE.PointsMaterial({
      size: 4,
      vertexColors: true,
      transparent: true,
      opacity: 0.5,
      blending: THREE.AdditiveBlending,
    });

    const particleSystem = new THREE.Points(geometry, particleMaterial);
    scene.add(particleSystem);

    // 2. Tasteful Floating Mini 3D Diamond Ornaments (6 Subtle Geometry Gems)
    const gemGroup = new THREE.Group();
    const gems: THREE.Mesh[] = [];

    for (let i = 0; i < 6; i++) {
      const size = 18 + Math.random() * 20;
      const gemGeo =
        i % 2 === 0
          ? new THREE.OctahedronGeometry(size, 0)
          : new THREE.IcosahedronGeometry(size, 0);

      const gemMat = new THREE.MeshBasicMaterial({
        color: i % 2 === 0 ? color1 : color2,
        wireframe: true,
        transparent: true,
        opacity: 0.25,
      });

      const gemMesh = new THREE.Mesh(gemGeo, gemMat);
      gemMesh.position.set(
        (Math.random() - 0.5) * 1100,
        (Math.random() - 0.5) * 800,
        (Math.random() - 0.5) * 500 - 50
      );

      gemGroup.add(gemMesh);
      gems.push(gemMesh);
    }
    scene.add(gemGroup);

    // 3. Elegant Perspective Floor Grid
    const gridHelper = new THREE.GridHelper(1800, 36, color1, 0x111827);
    gridHelper.position.y = -380;
    gridHelper.position.z = -100;
    (gridHelper.material as THREE.Material).transparent = true;
    (gridHelper.material as THREE.Material).opacity = 0.22;
    scene.add(gridHelper);

    // Mouse Tracking Parallax
    let mouseX = 0;
    let mouseY = 0;

    const handleMouseMove = (event: MouseEvent) => {
      mouseX = (event.clientX - window.innerWidth / 2) * 0.1;
      mouseY = (event.clientY - window.innerHeight / 2) * 0.1;
    };

    window.addEventListener("mousemove", handleMouseMove);

    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };

    window.addEventListener("resize", handleResize);

    // Animation Loop
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      const elapsedTime = clock.getElapsedTime();

      const currentColor1 = new THREE.Color(themeRef.current.primary);
      const currentColor2 = new THREE.Color(themeRef.current.secondary);

      // Smooth camera drift based on mouse
      camera.position.x += (mouseX * 0.5 - camera.position.x) * 0.03;
      camera.position.y += (-mouseY * 0.5 - camera.position.y) * 0.03;
      camera.lookAt(scene.position);

      // Ambient particle drift & theme color morph
      const posAttr = geometry.attributes.position as THREE.BufferAttribute;
      const posArr = posAttr.array as Float32Array;
      const colAttr = geometry.attributes.color as THREE.BufferAttribute;
      const colArr = colAttr.array as Float32Array;

      for (let i = 0; i < particleCount; i++) {
        const idx = i * 3;
        posArr[idx] += speeds[idx];
        posArr[idx + 1] += speeds[idx + 1];

        if (Math.abs(posArr[idx]) > 650) posArr[idx] *= -0.95;
        if (Math.abs(posArr[idx + 1]) > 550) posArr[idx + 1] *= -0.95;

        // Smooth theme color interpolation
        const mix = (Math.sin(elapsedTime * 0.4 + i) + 1) / 2;
        const c = currentColor1.clone().lerp(currentColor2, mix);
        colArr[idx] = c.r;
        colArr[idx + 1] = c.g;
        colArr[idx + 2] = c.b;
      }
      posAttr.needsUpdate = true;
      colAttr.needsUpdate = true;

      // Rotate floating mini gems
      gems.forEach((gem, idx) => {
        gem.rotation.x += 0.006 * (idx % 2 === 0 ? 1 : -1);
        gem.rotation.y += 0.009 * (idx % 3 === 0 ? 1 : -1);
        gem.position.y += Math.sin(elapsedTime * 0.8 + idx) * 0.3;

        (gem.material as THREE.MeshBasicMaterial).color =
          idx % 2 === 0 ? currentColor1 : currentColor2;
      });

      particleSystem.rotation.y = elapsedTime * 0.015;

      renderer.render(scene, camera);
      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("resize", handleResize);
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      geometry.dispose();
      particleMaterial.dispose();
      renderer.dispose();
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 pointer-events-none z-0 overflow-hidden opacity-75"
    />
  );
}
