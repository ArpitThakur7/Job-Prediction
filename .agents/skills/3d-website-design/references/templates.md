# GitHub 3D Website Design Templates & Code Reference

This reference document archives open-source patterns, GLTF loaders, shaders, and component setups sourced from top GitHub 3D web development repositories.

---

## Source GitHub Repositories & Resources

1. **`adrianhajdin/3d-portfolio`** ([GitHub Link](https://github.com/adrianhajdin/3d-portfolio))
   - *Key Patterns*: 3D Hacker Room GLTF scene, interactive computers/screens, camera rotation bounds, loading bar fallback.
2. **`pmndrs/react-three-next`** ([GitHub Link](https://github.com/pmndrs/react-three-next))
   - *Key Patterns*: Next.js App Router + R3F Canvas integration, hybrid 2D/3D layout architecture, dynamic imports without SSR hydration errors.
3. **`sanidhyy/3d_portfolio`** ([GitHub Link](https://github.com/sanidhyy/3d_portfolio))
   - *Key Patterns*: Bento-grid 3D cards, canvas OrbitControls bounds, custom lighting rigs (`Environment` + `directionalLight`).
4. **`brunosimon/my-portfolio-2019`** ([GitHub Link](https://github.com/brunosimon/my-portfolio-2019))
   - *Key Patterns*: Cannon.js physics world integration, floor shadow projections, car driving physics control in WebGL.
5. **`doinel1a/vite-three-js`** ([GitHub Link](https://github.com/doinel1a/vite-three-js))
   - *Key Patterns*: Custom GLSL shader material setup (vertex shader + fragment shader + uniforms).

---

## Code Templates & Implementations

### 1. Next.js App Router R3F Canvas Container (`R3FCanvasContainer.tsx`)
*Sourced from `pmndrs/react-three-next`*

```tsx
"use client";

import React, { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { Environment, Loader } from "@react-three/drei";

export function R3FCanvasContainer({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative w-full h-full min-h-[400px]">
      <Canvas
        camera={{ position: [0, 0, 5], fov: 45 }}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        dpr={[1, 2]}
      >
        <ambientLight intensity={0.7} />
        <directionalLight position={[10, 10, 5]} intensity={1.2} />
        <Suspense fallback={null}>
          {children}
          <Environment preset="city" />
        </Suspense>
      </Canvas>
      <Loader />
    </div>
  );
}
```

---

### 2. 3D GLTF Interactive Room / Model Scene (`HackerRoomScene.tsx`)
*Sourced from `adrianhajdin/3d-portfolio`*

```tsx
"use client";

import React, { useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { useGLTF, Float, OrbitControls, MeshWobbleMaterial } from "@react-three/drei";
import * as THREE from "three";

function HackerRoomModel({ modelPath }: { modelPath: string }) {
  const { scene } = useGLTF(modelPath);
  const modelRef = useRef<THREE.Group>(null!);

  useFrame((state, delta) => {
    modelRef.current.rotation.y += delta * 0.15;
  });

  return (
    <Float speed={1.5} rotationIntensity={0.5} floatIntensity={1}>
      <group ref={modelRef} scale={1.2} position={[0, -0.5, 0]}>
        <primitive object={scene} />
      </group>
    </Float>
  );
}

export function HackerRoomScene({ modelPath }: { modelPath: string }) {
  return (
    <div className="w-full h-[550px] bg-slate-950 rounded-2xl overflow-hidden border border-slate-800">
      <Canvas camera={{ position: [0, 1.5, 4], fov: 45 }}>
        <ambientLight intensity={0.8} />
        <directionalLight position={[5, 10, 5]} intensity={1.5} color="#818cf8" />
        <pointLight position={[-5, -5, -5]} intensity={0.6} color="#c084fc" />
        <HackerRoomModel modelPath={modelPath} />
        <OrbitControls enableZoom={false} maxPolarAngle={Math.PI / 2} minPolarAngle={Math.PI / 3} />
      </Canvas>
    </div>
  );
}
```

---

### 3. Custom GLSL Shader Wave Background (`ShaderWave3D.tsx`)
*Sourced from `doinel1a/vite-three-js`*

```tsx
"use client";

import React, { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

const vertexShader = `
  uniform float uTime;
  varying vec2 vUv;
  varying float vElevation;

  void main() {
    vUv = uv;
    vec4 modelPosition = modelMatrix * vec4(position, 1.0);
    float elevation = sin(modelPosition.x * 3.0 + uTime * 2.0) * 0.15 + sin(modelPosition.z * 2.0 + uTime * 1.5) * 0.15;
    modelPosition.y += elevation;
    vElevation = elevation;
    gl_Position = projectionMatrix * viewMatrix * modelPosition;
  }
`;

const fragmentShader = `
  varying vec2 vUv;
  varying float vElevation;
  uniform vec3 uDepthColor;
  uniform vec3 uSurfaceColor;

  void main() {
    float mixStrength = (vElevation + 0.15) * 2.5;
    vec3 color = mix(uDepthColor, uSurfaceColor, mixStrength);
    gl_FragColor = vec4(color, 0.85);
  }
`;

function WaveMesh() {
  const meshRef = useRef<THREE.Mesh>(null!);
  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uDepthColor: { value: new THREE.Color("#090d16") },
      uSurfaceColor: { value: new THREE.Color("#4f46e5") },
    }),
    []
  );

  useFrame((state, delta) => {
    if (meshRef.current) {
      (meshRef.current.material as THREE.ShaderMaterial).uniforms.uTime.value += delta;
    }
  });

  return (
    <mesh ref={meshRef} rotation={[-Math.PI / 3, 0, 0]}>
      <planeGeometry args={[10, 10, 64, 64]} />
      <shaderMaterial
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
        transparent
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

export function ShaderWave3D() {
  return (
    <div className="w-full h-[450px] bg-slate-950 rounded-2xl overflow-hidden">
      <Canvas camera={{ position: [0, 2, 4], fov: 50 }}>
        <WaveMesh />
      </Canvas>
    </div>
  );
}
```
