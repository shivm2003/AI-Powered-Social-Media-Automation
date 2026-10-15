"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import styles from "./ThreeDScene.module.css";

export default function ThreeDScene() {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const [coords, setCoords] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    // Scene Setup
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x0a0a14, 0.035);

    // Camera Setup
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 480;
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
    camera.position.set(0, 0, 7.5);

    // Renderer Setup
    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({
        canvas,
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
      });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.25;
    } catch (e) {
      console.warn("WebGL initialization failed:", e);
      return;
    }

    // Master Group for Parallax
    const masterGroup = new THREE.Group();
    scene.add(masterGroup);

    // 1. Central Holographic Core (Icosahedron)
    const coreGeo = new THREE.IcosahedronGeometry(1.6, 1);
    const coreMat = new THREE.MeshPhysicalMaterial({
      color: 0x7c3aed,
      emissive: 0x2e1065,
      emissiveIntensity: 0.6,
      roughness: 0.15,
      metalness: 0.85,
      transmission: 0.3,
      ior: 1.4,
      wireframe: false,
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    masterGroup.add(coreMesh);

    // 2. Outer Wireframe Cage
    const wireGeo = new THREE.IcosahedronGeometry(1.85, 1);
    const wireMat = new THREE.MeshBasicMaterial({
      color: 0x00f5ff,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    });
    const wireMesh = new THREE.Mesh(wireGeo, wireMat);
    masterGroup.add(wireMesh);

    // 3. Inner Pulsing Core
    const innerGeo = new THREE.SphereGeometry(0.85, 32, 32);
    const innerMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      wireframe: false,
      transparent: true,
      opacity: 0.75,
    });
    const innerMesh = new THREE.Mesh(innerGeo, innerMat);
    masterGroup.add(innerMesh);

    // 4. Orbital Rings (Torus)
    const ring1Geo = new THREE.TorusGeometry(2.6, 0.025, 16, 100);
    const ring1Mat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.6,
    });
    const ring1 = new THREE.Mesh(ring1Geo, ring1Mat);
    ring1.rotation.x = Math.PI / 3;
    ring1.rotation.y = Math.PI / 6;
    masterGroup.add(ring1);

    const ring2Geo = new THREE.TorusGeometry(3.1, 0.02, 16, 100);
    const ring2Mat = new THREE.MeshBasicMaterial({
      color: 0xa855f7,
      transparent: true,
      opacity: 0.5,
    });
    const ring2 = new THREE.Mesh(ring2Geo, ring2Mat);
    ring2.rotation.x = -Math.PI / 4;
    ring2.rotation.y = Math.PI / 4;
    masterGroup.add(ring2);

    const ring3Geo = new THREE.TorusGeometry(3.6, 0.018, 16, 100);
    const ring3Mat = new THREE.MeshBasicMaterial({
      color: 0xec4899,
      transparent: true,
      opacity: 0.4,
    });
    const ring3 = new THREE.Mesh(ring3Geo, ring3Mat);
    ring3.rotation.x = Math.PI / 2.2;
    masterGroup.add(ring3);

    // 5. Orbiting Satellites (Data Nodes)
    const satellites = [];
    const satGeo = new THREE.SphereGeometry(0.08, 16, 16);
    const satColors = [0x38bdf8, 0xa855f7, 0x10b981, 0xf59e0b];
    for (let i = 0; i < 6; i++) {
      const satMat = new THREE.MeshBasicMaterial({
        color: satColors[i % satColors.length],
      });
      const sat = new THREE.Mesh(satGeo, satMat);
      satellites.push({
        mesh: sat,
        radius: 2.5 + (i * 0.25),
        speed: 0.015 + (i * 0.005),
        angle: (i * Math.PI) / 3,
        tilt: (i * 0.4),
      });
      masterGroup.add(sat);
    }

    // 6. Particle Nebula / Starfield (BufferGeometry)
    const particleCount = 650;
    const particlePositions = new Float32Array(particleCount * 3);
    const particleColors = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
      const i3 = i * 3;
      particlePositions[i3] = (Math.random() - 0.5) * 16;
      particlePositions[i3 + 1] = (Math.random() - 0.5) * 12;
      particlePositions[i3 + 2] = (Math.random() - 0.5) * 12;

      // Color variation between cyan and purple
      const mixed = Math.random();
      particleColors[i3] = 0.2 + 0.5 * mixed;     // R
      particleColors[i3 + 1] = 0.6 - 0.3 * mixed; // G
      particleColors[i3 + 2] = 0.9 + 0.1 * mixed; // B
    }

    const particleGeo = new THREE.BufferGeometry();
    particleGeo.setAttribute("position", new THREE.BufferAttribute(particlePositions, 3));
    particleGeo.setAttribute("color", new THREE.BufferAttribute(particleColors, 3));

    const particleMat = new THREE.PointsMaterial({
      size: 0.06,
      vertexColors: true,
      transparent: true,
      opacity: 0.75,
      blending: THREE.AdditiveBlending,
    });
    const particleField = new THREE.Points(particleGeo, particleMat);
    scene.add(particleField);

    // 7. Dynamic Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);

    const lightCyan = new THREE.PointLight(0x00f5ff, 4, 15);
    lightCyan.position.set(4, 3, 3);
    scene.add(lightCyan);

    const lightPurple = new THREE.PointLight(0xa855f7, 5, 15);
    lightPurple.position.set(-4, -3, 2);
    scene.add(lightPurple);

    // Mouse Tracking & Parallax
    let targetX = 0;
    let targetY = 0;
    let mouseX = 0;
    let mouseY = 0;

    const handleMouseMove = (e) => {
      const rect = container.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const y = -(((e.clientY - rect.top) / rect.height) * 2 - 1);
      targetX = x * 0.8;
      targetY = y * 0.8;
      setCoords({
        x: Math.round(x * 100),
        y: Math.round(y * 100),
      });
    };

    const handleMouseEnter = () => setIsHovered(true);
    const handleMouseLeave = () => {
      setIsHovered(false);
      targetX = 0;
      targetY = 0;
    };

    container.addEventListener("mousemove", handleMouseMove);
    container.addEventListener("mouseenter", handleMouseEnter);
    container.addEventListener("mouseleave", handleMouseLeave);

    // Resize Handler
    const handleResize = () => {
      if (!container || !renderer) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener("resize", handleResize);

    // Animation Loop
    let animationFrameId;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Smooth camera parallax interpolation (LERP)
      mouseX += (targetX - mouseX) * 0.05;
      mouseY += (targetY - mouseY) * 0.05;

      camera.position.x = mouseX * 2.2;
      camera.position.y = mouseY * 1.8;
      camera.lookAt(0, 0, 0);

      // Core rotation
      coreMesh.rotation.x = elapsedTime * 0.35;
      coreMesh.rotation.y = elapsedTime * 0.45;

      wireMesh.rotation.x = -elapsedTime * 0.25;
      wireMesh.rotation.y = -elapsedTime * 0.3;

      // Inner pulse
      const pulseScale = 0.85 + Math.sin(elapsedTime * 3) * 0.08;
      innerMesh.scale.set(pulseScale, pulseScale, pulseScale);

      // Rings rotation
      ring1.rotation.z = elapsedTime * 0.4;
      ring2.rotation.z = -elapsedTime * 0.3;
      ring3.rotation.y = elapsedTime * 0.25;

      // Orbiting satellites
      satellites.forEach((sat) => {
        sat.angle += sat.speed;
        sat.mesh.position.x = Math.cos(sat.angle) * sat.radius;
        sat.mesh.position.y = Math.sin(sat.angle) * Math.sin(sat.tilt) * sat.radius;
        sat.mesh.position.z = Math.sin(sat.angle) * Math.cos(sat.tilt) * sat.radius;
      });

      // Background particle drift
      particleField.rotation.y = elapsedTime * 0.04;
      particleField.rotation.x = elapsedTime * 0.02;

      // Moving lights
      lightCyan.position.x = Math.sin(elapsedTime * 0.7) * 5;
      lightCyan.position.y = Math.cos(elapsedTime * 0.5) * 4;
      lightPurple.position.x = -Math.cos(elapsedTime * 0.6) * 5;
      lightPurple.position.y = -Math.sin(elapsedTime * 0.8) * 4;

      renderer.render(scene, camera);
    };

    animate();

    // Cleanup
    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", handleResize);
      container.removeEventListener("mousemove", handleMouseMove);
      container.removeEventListener("mouseenter", handleMouseEnter);
      container.removeEventListener("mouseleave", handleMouseLeave);

      // Dispose Three.js objects
      [coreGeo, wireGeo, innerGeo, ring1Geo, ring2Geo, ring3Geo, satGeo, particleGeo].forEach(g => g.dispose());
      [coreMat, wireMat, innerMat, ring1Mat, ring2Mat, ring3Mat, particleMat].forEach(m => m.dispose());
      if (renderer) renderer.dispose();
    };
  }, []);

  return (
    <div className={styles.canvasContainer} ref={containerRef}>
      <div className={styles.scanlineOverlay} />
      <canvas ref={canvasRef} className={styles.canvas} />

      {/* Futuristic HUD overlay */}
      <div className={styles.hudOverlay}>
        <div className={styles.hudTop}>
          <div className={styles.badge3D}>
            <span className={styles.pulseDot} />
            <span>Manvxi AI 3D Core Active</span>
          </div>
          <div className={styles.hudCoordinates}>
            PITCH: {coords.x}° | YAW: {coords.y}° | {isHovered ? "TRACKING" : "AUTOPILOT"}
          </div>
        </div>

        <div className={styles.hudBottom}>
          <div className={styles.hudTitleGroup}>
            <div className={styles.hudSubtitle}>
              <span>⚡</span> Autonomous Neural Engine
            </div>
            <h2 className={styles.hudTitle}>Manvxi AI Holographic Hub</h2>
          </div>
          <div className={styles.hudControlsTip}>
            <span>🖱️</span> Drag / move cursor to rotate 3D view
          </div>
        </div>
      </div>
    </div>
  );
}
