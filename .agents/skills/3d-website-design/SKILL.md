---
name: 3d-website-design
description: 3D website design patterns, React Three Fiber (R3F) templates, Three.js shaders, GLTF model loaders, particle background canvases, 3D card tilt physics, holographic globes, skill prisms, and camera scroll animations for web development. Sourced from top GitHub 3D web repos (adrianhajdin/3d-portfolio, pmndrs/react-three-next, sanidhyy/3d_portfolio, brunosimon/my-portfolio-2019, doinel1a/vite-three-js). Use when creating modern, interactive 3D landing pages, portfolios, or WebGL website visualizers.
---

# 3D Website Design & WebGL Architecture Guide

This skill provides production-ready React Three Fiber (R3F), Three.js, and WebGL templates and design patterns for building modern 3D web applications, directly referenced and adapted from leading open-source GitHub 3D website repositories.

---

## Direct GitHub Source References

* **[`adrianhajdin/3d-portfolio`](https://github.com/adrianhajdin/3d-portfolio)**: GLTF Hacker Room loading, camera constraints, interactive object hovers.
* **[`pmndrs/react-three-next`](https://github.com/pmndrs/react-three-next)**: Next.js App Router + R3F Canvas layout shell, non-SSR dynamic canvas mounting.
* **[`sanidhyy/3d_portfolio`](https://github.com/sanidhyy/3d_portfolio)**: Modern bento-grid 3D cards, lighting setups, orbit controls bounds.
* **[`brunosimon/my-portfolio-2019`](https://github.com/brunosimon/my-portfolio-2019)**: Physics-driven WebGL car & terrain controls.
* **[`doinel1a/vite-three-js`](https://github.com/doinel1a/vite-three-js)**: Custom GLSL vertex & fragment shader material setup.

---

## Core Tech Stack & Libraries

* **`three`**: Three.js WebGL rendering engine.
* **`@react-three/fiber` (`R3F`)**: Declarative React wrapper for Three.js.
* **`@react-three/drei`**: High-level Drei helpers (`useGLTF`, `Float`, `OrbitControls`, `ScrollControls`, `Html`, `MeshWobbleMaterial`, `Stars`, `Environment`, `PerspectiveCamera`).
* **`framer-motion`**: DOM UI micro-animations overlaying 3D canvases.
* **`lucide-react`**: Modern UI icon suite.

---

## 3D Website Design Architecture

### 1. Canvas Setup Best Practices
Always set `gl={{ antialias: true, alpha: true }}` and configure custom camera positions:
```tsx
import { Canvas } from "@react-three/fiber";

<Canvas
  camera={{ position: [0, 0, 5], fov: 50 }}
  gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
  dpr={[1, 2]}
  className="w-full h-full"
>
  <ambientLight intensity={0.6} />
  <directionalLight position={[10, 10, 5]} intensity={1.2} />
  <pointLight position={[-10, -10, -5]} intensity={0.5} />
  {/* 3D Scene Components */}
</Canvas>
```

### 2. Performance & Mobile Optimization Rules
1. **Model Preloading**: Always call `useGLTF.preload("/path/to/model.glb")` outside component definitions.
2. **DPR Capping**: Cap device pixel ratio: `dpr={[1, 2]}` to protect mobile GPU performance.
3. **Suspense Fallback**: Wrap 3D components in `<Suspense fallback={<Loader />}>`.
4. **Frame Loop Optimization**: Use `useFrame((state, delta) => ...)` instead of `requestAnimationFrame` for smooth frame updates.

---

## 3D Template Catalog

See detailed code references and implementations in [references/templates.md](file:///.agents/skills/3d-website-design/references/templates.md):

1. **Next.js R3F Canvas Shell**: Sourced from `pmndrs/react-three-next`.
2. **3D Hacker Room / Model Viewer**: Sourced from `adrianhajdin/3d-portfolio`.
3. **Custom GLSL Shader Wave Scene**: Sourced from `doinel1a/vite-three-js`.
4. **Particle Field & Dynamic Wave Background**: Interactive mouse-reactive WebGL starfield.
5. **Glassmorphic 3D Card Physics**: 3D tilt cards with perspective shadows.
6. **Holographic Globe 3D**: Rotating wireframe globe with spatial data nodes.
7. **Skill Matrix Prism 3D**: Rotating 3D crystal prism displaying skills vector nodes.
