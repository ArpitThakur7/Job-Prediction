"use client";

import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";

interface CareerPathProps {
  resumeData?: any;
  matchResults?: any[];
}

export default function CareerPathHorizon3D({ resumeData, matchResults }: CareerPathProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [activeMilestone, setActiveMilestone] = useState<number>(1);

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 340;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
    camera.position.set(0, 2.5, 6);
    camera.lookAt(0, 0, -8);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Lighting
    const ambLight = new THREE.AmbientLight(0xffffff, 1.2);
    scene.add(ambLight);

    const indigoDirLight = new THREE.DirectionalLight(0x4f46e5, 2.5);
    indigoDirLight.position.set(0, 10, 5);
    scene.add(indigoDirLight);

    const tealPointLight = new THREE.PointLight(0x0ea5e9, 2, 40);
    tealPointLight.position.set(0, 2, -10);
    scene.add(tealPointLight);

    // 1. Glowing 3D Indigo Curved Road into Horizon
    const roadCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(0, -0.5, 3),
      new THREE.Vector3(-0.8, -0.3, -2),
      new THREE.Vector3(0.8, -0.1, -8),
      new THREE.Vector3(0, 0.2, -16),
    ]);

    const tubeGeo = new THREE.TubeGeometry(roadCurve, 100, 0.8, 16, false);
    const tubeMat = new THREE.MeshStandardMaterial({
      color: 0x4f46e5,
      roughness: 0.2,
      metalness: 0.8,
      emissive: 0x4f46e5,
      emissiveIntensity: 0.4,
      wireframe: false,
    });
    const roadMesh = new THREE.Mesh(tubeGeo, tubeMat);
    scene.add(roadMesh);

    // Road Wireframe Accents
    const wireGeo = new THREE.TubeGeometry(roadCurve, 100, 0.84, 12, false);
    const wireMat = new THREE.MeshBasicMaterial({
      color: 0x0ea5e9,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    });
    const wireMesh = new THREE.Mesh(wireGeo, wireMat);
    scene.add(wireMesh);

    // 2. Milestone 3D Floating Crystals
    const milestoneNodes: THREE.Mesh[] = [];
    const positions = [
      new THREE.Vector3(-0.6, 0.6, 0.5),   // Milestone 1: Current Skills
      new THREE.Vector3(0.5, 0.9, -4.5),   // Milestone 2: Skill Gap
      new THREE.Vector3(0, 1.2, -11.5),    // Milestone 3: Dream Job
    ];

    positions.forEach((pos, idx) => {
      const crystalGeo = new THREE.OctahedronGeometry(0.45, 0);
      const crystalMat = new THREE.MeshStandardMaterial({
        color: idx === 0 ? 0x10b981 : idx === 1 ? 0xf97316 : 0x4f46e5,
        emissive: idx === 0 ? 0x10b981 : idx === 1 ? 0xf97316 : 0x4f46e5,
        emissiveIntensity: 0.6,
        roughness: 0.1,
        metalness: 0.9,
      });
      const crystalMesh = new THREE.Mesh(crystalGeo, crystalMat);
      crystalMesh.position.copy(pos);
      scene.add(crystalMesh);
      milestoneNodes.push(crystalMesh);
    });

    // 3. Upward Floating Sparkles along the Road
    const particleCount = 100;
    const particleGeo = new THREE.BufferGeometry();
    const posArr = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
      posArr[i * 3] = (Math.random() - 0.5) * 8;
      posArr[i * 3 + 1] = Math.random() * 4 - 1;
      posArr[i * 3 + 2] = -Math.random() * 16;
    }

    particleGeo.setAttribute("position", new THREE.BufferAttribute(posArr, 3));
    const particleMat = new THREE.PointsMaterial({
      size: 0.07,
      color: 0x0ea5e9,
      transparent: true,
      opacity: 0.7,
    });
    const particleSystem = new THREE.Points(particleGeo, particleMat);
    scene.add(particleSystem);

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

      milestoneNodes.forEach((node, idx) => {
        node.rotation.y = time * (1 + idx * 0.3);
        node.position.y = positions[idx].y + Math.sin(time * 2 + idx) * 0.12;
      });

      particleSystem.rotation.z = time * 0.02;

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
      tubeGeo.dispose();
      tubeMat.dispose();
      wireGeo.dispose();
      wireMat.dispose();
      particleGeo.dispose();
      particleMat.dispose();
      milestoneNodes.forEach((n) => {
        n.geometry.dispose();
        if (Array.isArray(n.material)) {
          n.material.forEach((m) => m.dispose());
        } else {
          n.material.dispose();
        }
      });
      renderer.dispose();
    };
  }, []);

  // Build milestone data from real resume/match results
  const currentSkills = resumeData?.skills || [];
  const currentSkillsStr = currentSkills.length > 0
    ? currentSkills.slice(0, 6).join(", ") + (currentSkills.length > 6 ? ` +${currentSkills.length - 6} more` : "")
    : "Python, FastAPI, React, SQL & Data Pipelines";

  // Derive skill gaps from top matched jobs
  const getSkillGaps = () => {
    if (!matchResults || matchResults.length === 0 || !currentSkills.length) {
      return "+15% AWS Cloud & Docker containerization recommended for top tier.";
    }
    const currentSet = new Set(currentSkills.map((s: string) => s.toLowerCase()));
    const gapSkills: string[] = [];
    for (const match of matchResults.slice(0, 5)) {
      const reqSkills = match.required_skills || [];
      for (const s of reqSkills) {
        const sl = typeof s === "string" ? s.toLowerCase() : "";
        if (sl && !currentSet.has(sl) && !gapSkills.map(g => g.toLowerCase()).includes(sl)) {
          gapSkills.push(s);
        }
      }
    }
    if (gapSkills.length === 0) return "Your skills cover most top job requirements. Consider deepening specializations.";
    return `Gap skills to boost matches: ${gapSkills.slice(0, 4).join(", ")}${gapSkills.length > 4 ? ` +${gapSkills.length - 4} more` : ""}.`;
  };

  // Dream role from top match
  const getDreamRole = () => {
    if (!matchResults || matchResults.length === 0) {
      return "Senior ML Engineer / Lead Full-Stack Architect ($145k - $185k).";
    }
    const top = matchResults[0];
    const title = top.title || "Senior Engineer";
    const company = top.company || "Top Enterprise";
    const salMin = top.salary_min ? `$${(top.salary_min / 1000).toFixed(0)}k` : "$120k";
    const salMax = top.salary_max ? `$${(top.salary_max / 1000).toFixed(0)}k` : "$180k";
    const score = top.match_score || top.raw_score || 0.9;
    const scoreStr = typeof score === "string" ? score : `${(score * 100).toFixed(0)}%`;
    return `${title} at ${company} (${salMin} - ${salMax}) — ${scoreStr} match.`;
  };

  const milestones = [
    {
      step: 1,
      title: "Current Verified Skills",
      desc: currentSkillsStr + " parsed from resume.",
      color: "border-emerald-300 text-emerald-700 bg-emerald-50",
      badge: currentSkills.length > 0 ? `${currentSkills.length} Skills` : "Completed",
    },
    {
      step: 2,
      title: "AI Skill Gap Analysis",
      desc: getSkillGaps(),
      color: "border-orange-300 text-orange-700 bg-orange-50",
      badge: "In Progress",
    },
    {
      step: 3,
      title: "Predicted Dream Role",
      desc: getDreamRole(),
      color: "border-indigo-300 text-indigo-700 bg-indigo-50",
      badge: "Target Goal",
    },
  ];

  return (
    <div className="relative w-full rounded-3xl overflow-hidden glass-panel shadow-2xl p-6">
      
      {/* Signature Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4 z-10 relative">
        <div>
          <span className="text-xs font-mono font-bold uppercase tracking-widest text-[#4F46E5] bg-[#E0E7FF] px-3.5 py-1 rounded-full border border-[#c7d2fe]">
            💎 SIGNATURE VISUALIZER
          </span>
          <h3 className="text-2xl font-black text-slate-900 mt-2 font-heading">
            Your 3D Career Path Horizon
          </h3>
          <p className="text-xs text-slate-500 font-medium">
            AI-generated career road mapping your skills directly to your predicted dream role.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-[#10B981] animate-ping" />
          <span className="text-xs font-mono font-bold text-[#10B981]">Real-time Pathing</span>
        </div>
      </div>

      {/* 3D WebGL Curved Road Canvas */}
      <div className="relative w-full h-[320px]">
        <div ref={containerRef} className="w-full h-full" />
      </div>

      {/* Interactive Milestone Cards Overlay */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4 pt-4 border-t border-[#E0E7FF] font-sans">
        {milestones.map((m) => (
          <div
            key={m.step}
            onClick={() => setActiveMilestone(m.step)}
            className={`p-4 rounded-2xl border transition-all cursor-pointer shadow-sm hover:shadow-md ${
              activeMilestone === m.step
                ? `${m.color} ring-2 ring-[#4F46E5]/40 scale-102`
                : "bg-white/80 border-[#E0E7FF] hover:border-[#4F46E5]/30 text-slate-700"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-mono font-bold uppercase px-2.5 py-0.5 rounded-full bg-white/90 shadow-xs border border-slate-200">
                Step 0{m.step}
              </span>
              <span className="text-[10px] font-mono font-extrabold uppercase tracking-wide">
                {m.badge}
              </span>
            </div>
            <h4 className="font-bold text-slate-900 text-sm">{m.title}</h4>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">{m.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
