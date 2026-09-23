"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";
import { useApp } from "@/context/AppContext";

export type StructureType =
  | "database"
  | "matches"
  | "crystal"
  | "telemetry"
  | "document"
  | "radar"
  | "bot";

interface Card3DCanvasProps {
  structure: StructureType;
  size?: number;
}

export default function Card3DCanvas({
  structure,
  size = 110,
}: Card3DCanvasProps) {
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

    const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
    camera.position.z = 120;

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: "high-performance",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(size, size);
    container.appendChild(renderer.domElement);

    const group = new THREE.Group();

    const color1 = new THREE.Color(themeRef.current.primary);
    const color2 = new THREE.Color(themeRef.current.secondary);

    // Build unique 3D Structure based on type
    if (structure === "database") {
      // 3D Rotating Database Cylinder Stack
      for (let i = 0; i < 3; i++) {
        const cylGeo = new THREE.CylinderGeometry(24, 24, 8, 20);
        const cylMat = new THREE.MeshBasicMaterial({
          color: i === 1 ? color2 : color1,
          wireframe: true,
          transparent: true,
          opacity: 0.8,
        });
        const cylMesh = new THREE.Mesh(cylGeo, cylMat);
        cylMesh.position.y = (i - 1) * 14;
        group.add(cylMesh);
      }
    } else if (structure === "matches") {
      // 3D Target Matrix Ring
      const ringGeo = new THREE.TorusGeometry(26, 4, 16, 40);
      const ringMat = new THREE.MeshBasicMaterial({
        color: color2,
        wireframe: true,
        transparent: true,
        opacity: 0.85,
      });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      group.add(ringMesh);

      const innerGeo = new THREE.OctahedronGeometry(12, 0);
      const innerMat = new THREE.MeshBasicMaterial({
        color: color1,
        transparent: true,
        opacity: 0.7,
      });
      const innerMesh = new THREE.Mesh(innerGeo, innerMat);
      group.add(innerMesh);
    } else if (structure === "crystal") {
      // 3D Energy Crystal Tetrahedron
      const tetGeo = new THREE.TetrahedronGeometry(28, 0);
      const tetMat = new THREE.MeshBasicMaterial({
        color: color1,
        wireframe: true,
        transparent: true,
        opacity: 0.9,
      });
      const tetMesh = new THREE.Mesh(tetGeo, tetMat);
      group.add(tetMesh);

      const icoGeo = new THREE.IcosahedronGeometry(14, 1);
      const icoMat = new THREE.MeshBasicMaterial({
        color: color2,
        transparent: true,
        opacity: 0.6,
      });
      const icoMesh = new THREE.Mesh(icoGeo, icoMat);
      group.add(icoMesh);
    } else if (structure === "telemetry") {
      // 3D Spinning Neural Core
      const sphereGeo = new THREE.SphereGeometry(22, 16, 16);
      const sphereMat = new THREE.MeshBasicMaterial({
        color: color2,
        wireframe: true,
        transparent: true,
        opacity: 0.8,
      });
      const sphereMesh = new THREE.Mesh(sphereGeo, sphereMat);
      group.add(sphereMesh);

      const ringGeo = new THREE.TorusGeometry(32, 1.5, 12, 30);
      const ringMat = new THREE.MeshBasicMaterial({
        color: color1,
      });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.rotation.x = Math.PI * 0.3;
      group.add(ringMesh);
    } else if (structure === "document") {
      // 3D Scanner Document Mesh
      const docGeo = new THREE.BoxGeometry(32, 42, 3);
      const docMat = new THREE.MeshBasicMaterial({
        color: color1,
        wireframe: true,
        transparent: true,
        opacity: 0.85,
      });
      const docMesh = new THREE.Mesh(docGeo, docMat);
      group.add(docMesh);

      // Scanning bar
      const barGeo = new THREE.BoxGeometry(38, 2, 4);
      const barMat = new THREE.MeshBasicMaterial({ color: color2 });
      const barMesh = new THREE.Mesh(barGeo, barMat);
      barMesh.name = "scanBar";
      group.add(barMesh);
    } else if (structure === "radar") {
      // 3D Radar Dish Matrix
      const coneGeo = new THREE.ConeGeometry(28, 18, 16, 1, true);
      const coneMat = new THREE.MeshBasicMaterial({
        color: color2,
        wireframe: true,
        transparent: true,
        opacity: 0.85,
      });
      const coneMesh = new THREE.Mesh(coneGeo, coneMat);
      coneMesh.rotation.x = -Math.PI * 0.4;
      group.add(coneMesh);

      const centerGeo = new THREE.SphereGeometry(6, 12, 12);
      const centerMat = new THREE.MeshBasicMaterial({ color: color1 });
      const centerMesh = new THREE.Mesh(centerGeo, centerMat);
      group.add(centerMesh);
    } else if (structure === "bot") {
      // 3D AI Bot Head Sphere
      const botGeo = new THREE.IcosahedronGeometry(22, 1);
      const botMat = new THREE.MeshBasicMaterial({
        color: color1,
        wireframe: true,
        transparent: true,
        opacity: 0.9,
      });
      const botMesh = new THREE.Mesh(botGeo, botMat);
      group.add(botMesh);

      const eyeGeo = new THREE.SphereGeometry(5, 12, 12);
      const eyeMat = new THREE.MeshBasicMaterial({ color: color2 });
      const eyeMesh = new THREE.Mesh(eyeGeo, eyeMat);
      group.add(eyeMesh);
    }

    scene.add(group);

    // Animation loop
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      const elapsedTime = clock.getElapsedTime();

      group.rotation.y = elapsedTime * 0.8;
      group.rotation.x = Math.sin(elapsedTime * 0.5) * 0.2;

      // Scan bar animation if document
      const scanBar = group.getObjectByName("scanBar");
      if (scanBar) {
        scanBar.position.y = Math.sin(elapsedTime * 3) * 18;
      }

      renderer.render(scene, camera);
      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, [size, structure]);

  return (
    <div
      ref={containerRef}
      className="pointer-events-none flex items-center justify-center shrink-0"
    />
  );
}
