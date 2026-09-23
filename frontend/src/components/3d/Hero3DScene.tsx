"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";

export default function Hero3DScene() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || 560;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 0, 7);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Warm Directional & Ambient Lighting
    const ambLight = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambLight);

    const warmLight = new THREE.DirectionalLight(0xffedd5, 1.8);
    warmLight.position.set(10, 15, 10);
    scene.add(warmLight);

    const indigoPointLight = new THREE.PointLight(0x4f46e5, 1.5, 50);
    indigoPointLight.position.set(-6, -2, 4);
    scene.add(indigoPointLight);

    const mainGroup = new THREE.Group();

    // 1. Floating 3D Resume Document Mesh
    const docGroup = new THREE.Group();
    docGroup.position.set(-1.2, 0.2, 0);

    const docGeo = new THREE.BoxGeometry(1.6, 2.2, 0.08);
    const docMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      roughness: 0.2,
      metalness: 0.1,
    });
    const docMesh = new THREE.Mesh(docGeo, docMat);
    docGroup.add(docMesh);

    // Resume Lines (CSS/WebGL simulation)
    for (let i = 0; i < 4; i++) {
      const lineGeo = new THREE.PlaneGeometry(1.1, 0.1);
      const lineMat = new THREE.MeshBasicMaterial({ color: 0x4f46e5 });
      const lineMesh = new THREE.Mesh(lineGeo, lineMat);
      lineMesh.position.set(0, 0.6 - i * 0.4, 0.05);
      docGroup.add(lineMesh);
    }
    mainGroup.add(docGroup);

    // 2. Floating 3D Briefcase Mesh
    const caseGroup = new THREE.Group();
    caseGroup.position.set(1.4, -0.1, 0.4);

    const caseBodyGeo = new THREE.BoxGeometry(1.8, 1.3, 0.5);
    const caseBodyMat = new THREE.MeshStandardMaterial({
      color: 0x4f46e5,
      roughness: 0.3,
      metalness: 0.7,
    });
    const caseBodyMesh = new THREE.Mesh(caseBodyGeo, caseBodyMat);
    caseGroup.add(caseBodyMesh);

    // Briefcase Handle
    const handleGeo = new THREE.TorusGeometry(0.35, 0.06, 12, 24, Math.PI);
    const handleMat = new THREE.MeshStandardMaterial({ color: 0x0ea5e9, metalness: 0.9, roughness: 0.1 });
    const handleMesh = new THREE.Mesh(handleGeo, handleMat);
    handleMesh.position.set(0, 0.7, 0);
    handleMesh.rotation.x = Math.PI;
    caseGroup.add(handleMesh);

    mainGroup.add(caseGroup);
    scene.add(mainGroup);

    // 3. Upward Floating Light Data Particles
    const particleCount = 140;
    const particleGeo = new THREE.BufferGeometry();
    const posArr = new Float32Array(particleCount * 3);
    const speeds = new Float32Array(particleCount);

    for (let i = 0; i < particleCount; i++) {
      posArr[i * 3] = (Math.random() - 0.5) * 12;
      posArr[i * 3 + 1] = (Math.random() - 0.5) * 8;
      posArr[i * 3 + 2] = (Math.random() - 0.5) * 6;
      speeds[i] = 0.01 + Math.random() * 0.02;
    }

    particleGeo.setAttribute("position", new THREE.BufferAttribute(posArr, 3));
    const particleMat = new THREE.PointsMaterial({
      size: 0.08,
      color: 0x0ea5e9,
      transparent: true,
      opacity: 0.75,
    });
    const particleSystem = new THREE.Points(particleGeo, particleMat);
    scene.add(particleSystem);

    // Mouse Tracking Parallax Tilt Physics
    let targetMouseX = 0;
    let targetMouseY = 0;

    const handleMouseMove = (event: MouseEvent) => {
      targetMouseX = (event.clientX - window.innerWidth / 2) * 0.0015;
      targetMouseY = (event.clientY - window.innerHeight / 2) * 0.0015;
    };

    window.addEventListener("mousemove", handleMouseMove);

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

      // Mouse Tilt Parallax
      mainGroup.rotation.y += (targetMouseX - mainGroup.rotation.y) * 0.05;
      mainGroup.rotation.x += (targetMouseY - mainGroup.rotation.x) * 0.05;

      // Floating Rotations
      docGroup.position.y = 0.2 + Math.sin(time * 1.5) * 0.12;
      docGroup.rotation.z = Math.sin(time * 1.2) * 0.08;

      caseGroup.position.y = -0.1 + Math.sin(time * 1.8 + 1) * 0.14;
      caseGroup.rotation.y = Math.cos(time * 1.4) * 0.15;

      // Upward Data Particle Animation
      const positions = particleGeo.attributes.position.array as Float32Array;
      for (let i = 0; i < particleCount; i++) {
        positions[i * 3 + 1] += speeds[i];
        if (positions[i * 3 + 1] > 4) {
          positions[i * 3 + 1] = -4;
        }
      }
      particleGeo.attributes.position.needsUpdate = true;

      renderer.render(scene, camera);
      animId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("resize", handleResize);
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  return (
    <div className="relative w-full h-[520px] rounded-3xl overflow-hidden bg-gradient-to-b from-white/90 to-[#EEF2FF]/80 border border-[#E0E7FF] shadow-xl">
      <div ref={containerRef} className="w-full h-full" />
    </div>
  );
}
