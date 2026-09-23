"use client";

import React, { useEffect, useRef, useMemo } from "react";
import * as THREE from "three";

export default function SkillTagCloud3D({ skills }: { skills?: string[] }) {
  const containerRef = useRef<HTMLDivElement>(null);

  const defaultSkills = useMemo(() => [
    "Python", "FastAPI", "React 19", "Pinecone RAG", "Machine Learning",
    "MongoDB", "Docker", "AWS", "TypeScript", "Tailwind CSS",
    "Uvicorn", "LLaMA 3.3", "SentenceTransformers", "GraphQL", "Redis"
  ], []);

  const skillList = useMemo(() => skills && skills.length > 0 ? skills : defaultSkills, [skills, defaultSkills]);

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const width = container.clientWidth || 400;
    const height = container.clientHeight || 300;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
    camera.position.z = 6;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    const ambLight = new THREE.AmbientLight(0xffffff, 1.2);
    scene.add(ambLight);

    const tagGroup = new THREE.Group();
    const createdGeometries: THREE.BufferGeometry[] = [];
    const createdMaterials: THREE.Material[] = [];

    // Distribute skills evenly on a 3D Sphere Surface
    const count = skillList.length;
    const radius = 2.4;

    skillList.forEach((skill, i) => {
      const phi = Math.acos(-1 + (2 * i) / count);
      const theta = Math.sqrt(count * Math.PI) * phi;

      const x = radius * Math.cos(theta) * Math.sin(phi);
      const y = radius * Math.sin(theta) * Math.sin(phi);
      const z = radius * Math.cos(phi);

      const sphereGeo = new THREE.SphereGeometry(0.12, 16, 16);
      const sphereMat = new THREE.MeshStandardMaterial({
        color: i % 2 === 0 ? 0x4f46e5 : 0x0ea5e9,
        emissive: i % 2 === 0 ? 0x4f46e5 : 0x0ea5e9,
        emissiveIntensity: 0.5,
        roughness: 0.2,
      });
      createdGeometries.push(sphereGeo);
      createdMaterials.push(sphereMat);

      const nodeMesh = new THREE.Mesh(sphereGeo, sphereMat);
      nodeMesh.position.set(x, y, z);
      tagGroup.add(nodeMesh);
    });

    scene.add(tagGroup);

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
      tagGroup.rotation.y = time * 0.2;
      tagGroup.rotation.x = time * 0.1;

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
      createdGeometries.forEach((g) => g.dispose());
      createdMaterials.forEach((m) => m.dispose());
      renderer.dispose();
    };
  }, [skillList]);

  return (
    <div className="relative w-full h-[300px] rounded-2xl overflow-hidden bg-gradient-to-b from-white/90 to-[#EEF2FF]/90 border border-[#E0E7FF] shadow-lg flex items-center justify-center">
      <div ref={containerRef} className="w-full h-full" />
    </div>
  );
}
