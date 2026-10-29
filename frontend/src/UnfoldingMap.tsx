import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

type Props = { progressRef: { current: number }; className?: string };

/**
 * 3D Angled Dashboard Stage in Three.js.
 * Renders the real UPWIND Explorer interface on a floating, glass-edged 3D slab
 * that smoothly changes perspective, tilts, and zooms along a parallax scroll path,
 * highlighting key ground-truth coordinates with glowing pins and dimensional vectors.
 */
export default function UnfoldingMap({ progressRef, className = "" }: Props) {
  const mountRef = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<"loading" | "ready" | "fallback">("loading");

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    let disposed = false;
    let frame = 0;
    let visible = true;
    let renderer: THREE.WebGLRenderer | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let intersectionObserver: IntersectionObserver | null = null;

    // Mouse tracking for organic physical tilt
    const mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
    const onMouseMove = (e: MouseEvent) => {
      const rect = mount.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      mouse.targetX = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
      mouse.targetY = ((e.clientY - rect.top) / rect.height - 0.5) * 2;
    };
    window.addEventListener("mousemove", onMouseMove, { passive: true });

    const schedule = () => {
      if (!frame && visible && !document.hidden && !disposed) {
        frame = requestAnimationFrame(tick);
      }
    };

    const visibilityChange = () => {
      if (document.hidden && frame) {
        cancelAnimationFrame(frame);
        frame = 0;
      } else {
        schedule();
      }
    };

    // 1. Scene & Camera Setup
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(26, 1, 0.1, 100);
    camera.position.set(0, 0, 7.8);
    const cameraLookAt = new THREE.Vector3(0, 0, 0);

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Atmospheric Studio Lighting (Teal & Luminous Cyan)
    scene.add(new THREE.AmbientLight(0x0a1e24, 2.6));

    const keyLight = new THREE.DirectionalLight(0x5ec5c0, 3.4);
    keyLight.position.set(5, 6, 6);
    scene.add(keyLight);

    const rimLight = new THREE.DirectionalLight(0x194b54, 2.4);
    rimLight.position.set(-6, 2, -4);
    scene.add(rimLight);

    const specularLight = new THREE.PointLight(0x38b2ac, 1.8, 10);
    specularLight.position.set(0.8, 1.5, 3.2);
    scene.add(specularLight);

    // 2. The 3D Angled Dashboard Slab
    const dashboardSlab = new THREE.Group();
    scene.add(dashboardSlab);

    // Base slab dimensions
    const slabWidth = 5.2;
    const slabHeight = 3.1;
    const slabDepth = 0.06;

    // Load actual high-resolution dashboard screenshot
    const texLoader = new THREE.TextureLoader();
    const dashboardTex = texLoader.load("/landing/explorer-overview.png", () => {
      if (!disposed) schedule();
    });
    dashboardTex.colorSpace = THREE.SRGBColorSpace;
    dashboardTex.generateMipmaps = true;

    // Slab materials (Front screen, dark titanium sides, matte back)
    const frontMat = new THREE.MeshStandardMaterial({
      map: dashboardTex,
      roughness: 0.28,
      metalness: 0.12,
    });
    const edgeMat = new THREE.MeshStandardMaterial({
      color: 0x112d34,
      metalness: 0.85,
      roughness: 0.2,
      emissive: 0x091b20,
      emissiveIntensity: 0.4,
    });
    const backMat = new THREE.MeshStandardMaterial({
      color: 0x071518,
      roughness: 0.8,
      metalness: 0.2,
    });

    const slabMaterials = [
      edgeMat, // Right
      edgeMat, // Left
      edgeMat, // Top
      edgeMat, // Bottom
      frontMat, // Front
      backMat,  // Back
    ];

    const slabGeo = new THREE.BoxGeometry(slabWidth, slabHeight, slabDepth);
    const slabMesh = new THREE.Mesh(slabGeo, slabMaterials);
    dashboardSlab.add(slabMesh);

    // Glowing cyan bevel frame around the dashboard
    const frameGeo = new THREE.RingGeometry(slabWidth * 0.5, slabWidth * 0.505, 4);
    frameGeo.rotateZ(Math.PI / 4);
    frameGeo.scale(1, slabHeight / slabWidth, 1);
    const frameMat = new THREE.MeshBasicMaterial({
      color: 0x38b2ac,
      transparent: true,
      opacity: 0.45,
      side: THREE.DoubleSide,
    });
    const glowFrame = new THREE.Mesh(frameGeo, frameMat);
    glowFrame.position.z = slabDepth * 0.5 + 0.005;
    dashboardSlab.add(glowFrame);

    // 3. Dynamic 3D Markers on the Dashboard Surface
    // Coordinate mapping on dashboard screen: X in [-2.4, 2.4], Y in [-1.4, 1.4]
    // Normalized to map area:
    // Durham roughly at X = 0.72, Y = -0.15
    // Monitor at X = 0.55, Y = -0.24
    // NEI Facility at X = 0.92, Y = 0.12
    const MARKERS = {
      durham: { x: 0.72, y: -0.15, z: slabDepth * 0.5 },
      monitor: { x: 0.55, y: -0.24, z: slabDepth * 0.5 },
      facility: { x: 0.92, y: 0.12, z: slabDepth * 0.5 },
    };

    // 3A. Modeled Place Marker (Durham, NC - Glowing Emerald)
    const durhamGroup = new THREE.Group();
    durhamGroup.position.set(MARKERS.durham.x, MARKERS.durham.y, MARKERS.durham.z);
    dashboardSlab.add(durhamGroup);

    const durhamRingGeo = new THREE.RingGeometry(0.08, 0.11, 32);
    const durhamRingMat = new THREE.MeshBasicMaterial({
      color: 0x2da895,
      transparent: true,
      opacity: 0.85,
      side: THREE.DoubleSide,
    });
    const durhamRing = new THREE.Mesh(durhamRingGeo, durhamRingMat);
    durhamGroup.add(durhamRing);

    const durhamSpireGeo = new THREE.CylinderGeometry(0.012, 0.012, 0.28, 12);
    durhamSpireGeo.rotateX(Math.PI / 2);
    const durhamSpireMat = new THREE.MeshStandardMaterial({
      color: 0x2da895,
      emissive: 0x38b2ac,
      emissiveIntensity: 0.8,
    });
    const durhamSpire = new THREE.Mesh(durhamSpireGeo, durhamSpireMat);
    durhamSpire.position.z = 0.14;
    durhamGroup.add(durhamSpire);

    const durhamBeaconGeo = new THREE.SphereGeometry(0.038, 16, 16);
    const durhamBeaconMat = new THREE.MeshBasicMaterial({ color: 0x64d2c7 });
    const durhamBeacon = new THREE.Mesh(durhamBeaconGeo, durhamBeaconMat);
    durhamBeacon.position.z = 0.28;
    durhamGroup.add(durhamBeacon);

    // 3B. Regulatory Monitor Marker (AQS Station - Sapphire Blue)
    const monitorGroup = new THREE.Group();
    monitorGroup.position.set(MARKERS.monitor.x, MARKERS.monitor.y, MARKERS.monitor.z);
    dashboardSlab.add(monitorGroup);

    const monitorRingGeo = new THREE.RingGeometry(0.07, 0.095, 32);
    const monitorRingMat = new THREE.MeshBasicMaterial({
      color: 0x2c7ab3,
      transparent: true,
      opacity: 0.85,
      side: THREE.DoubleSide,
    });
    const monitorRing = new THREE.Mesh(monitorRingGeo, monitorRingMat);
    monitorGroup.add(monitorRing);

    const monitorSpireGeo = new THREE.CylinderGeometry(0.012, 0.012, 0.22, 12);
    monitorSpireGeo.rotateX(Math.PI / 2);
    const monitorSpireMat = new THREE.MeshStandardMaterial({
      color: 0x2c7ab3,
      emissive: 0x2c7ab3,
      emissiveIntensity: 0.7,
    });
    const monitorSpire = new THREE.Mesh(monitorSpireGeo, monitorSpireMat);
    monitorSpire.position.z = 0.11;
    monitorGroup.add(monitorSpire);

    const monitorBeaconGeo = new THREE.SphereGeometry(0.032, 16, 16);
    const monitorBeaconMat = new THREE.MeshBasicMaterial({ color: 0x54a5e0 });
    const monitorBeacon = new THREE.Mesh(monitorBeaconGeo, monitorBeaconMat);
    monitorBeacon.position.z = 0.22;
    monitorGroup.add(monitorBeacon);

    // 3C. Industrial Facility Marker (EPA NEI - Terracotta)
    const facilityGroup = new THREE.Group();
    facilityGroup.position.set(MARKERS.facility.x, MARKERS.facility.y, MARKERS.facility.z);
    dashboardSlab.add(facilityGroup);

    const facilityConeGeo = new THREE.ConeGeometry(0.045, 0.2, 12);
    facilityConeGeo.rotateX(Math.PI / 2);
    const facilityConeMat = new THREE.MeshStandardMaterial({
      color: 0xd96543,
      emissive: 0x9e381f,
      emissiveIntensity: 0.6,
    });
    const facilityCone = new THREE.Mesh(facilityConeGeo, facilityConeMat);
    facilityCone.position.z = 0.1;
    facilityGroup.add(facilityCone);

    // Connection vector between Durham place and the monitor
    const linkCurve = new THREE.QuadraticBezierCurve3(
      new THREE.Vector3(MARKERS.durham.x, MARKERS.durham.y, MARKERS.durham.z + 0.02),
      new THREE.Vector3(0.63, -0.18, MARKERS.durham.z + 0.14),
      new THREE.Vector3(MARKERS.monitor.x, MARKERS.monitor.y, MARKERS.monitor.z + 0.02)
    );
    const linkPoints = linkCurve.getPoints(24);
    const linkGeo = new THREE.BufferGeometry().setFromPoints(linkPoints);
    const linkMat = new THREE.LineDashedMaterial({
      color: 0x64d2c7,
      dashSize: 0.04,
      gapSize: 0.025,
      transparent: true,
      opacity: 0.85,
    });
    const linkLine = new THREE.Line(linkGeo, linkMat);
    linkLine.computeLineDistances();
    dashboardSlab.add(linkLine);

    // 4. Bioluminescent Floating Atmospheric Particles
    const particleCount = 85;
    const particleGeo = new THREE.BufferGeometry();
    const particlePos = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount * 3; i += 3) {
      particlePos[i] = (Math.random() - 0.5) * 6.5;
      particlePos[i + 1] = (Math.random() - 0.5) * 4.5;
      particlePos[i + 2] = (Math.random() - 0.5) * 3.5;
    }
    particleGeo.setAttribute("position", new THREE.BufferAttribute(particlePos, 3));
    const particleMat = new THREE.PointsMaterial({
      color: 0x64d2c7,
      size: 0.038,
      transparent: true,
      opacity: 0.65,
      blending: THREE.AdditiveBlending,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    scene.add(particles);

    // 5. Cleanup
    const cleanup = () => {
      disposed = true;
      if (frame) cancelAnimationFrame(frame);
      resizeObserver?.disconnect();
      intersectionObserver?.disconnect();
      document.removeEventListener("visibilitychange", visibilityChange);
      window.removeEventListener("mousemove", onMouseMove);
      if (renderer) {
        renderer.dispose();
        renderer.domElement.remove();
      }
      scene.traverse((obj) => {
        const m = obj as THREE.Mesh;
        if (m.geometry) m.geometry.dispose();
        if (Array.isArray(m.material)) m.material.forEach((mat) => mat.dispose());
        else m.material?.dispose();
      });
    };

    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    } catch {
      setState("fallback");
      return cleanup;
    }

    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.shadowMap.enabled = false;
    renderer.domElement.setAttribute("aria-hidden", "true");
    renderer.domElement.className = "unfolding-map-canvas";
    renderer.domElement.addEventListener("webglcontextlost", (event) => {
      event.preventDefault();
      setState("fallback");
    });
    mount.appendChild(renderer.domElement);

    const resize = () => {
      if (!renderer || !mount) return;
      const width = Math.max(1, mount.clientWidth);
      const height = Math.max(1, mount.clientHeight);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };
    resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(mount);
    resize();

    intersectionObserver = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (!visible && frame) {
        cancelAnimationFrame(frame);
        frame = 0;
      } else {
        schedule();
      }
    }, { rootMargin: "120px" });
    intersectionObserver.observe(mount);
    document.addEventListener("visibilitychange", visibilityChange);

    // 6. Smooth Parallax Scroll Render Loop
    let animClock = 0;
    const targetPos = new THREE.Vector3();
    const targetRot = new THREE.Euler();

    const render = () => {
      frame = 0;
      if (disposed || !renderer) return;

      animClock += 0.016;
      const p = reduceMotion ? 0.35 : Math.max(0, Math.min(1, progressRef.current));

      // Mouse inertia for responsive physical tilt
      mouse.x += (mouse.targetX - mouse.x) * 0.08;
      mouse.y += (mouse.targetY - mouse.y) * 0.08;

      // 3D Angled Dashboard Parallax Path:
      // Waypoint 0 (Hero 0.0 - 0.25): Isometric 3D angle (rotateX -0.42, rotateY 0.28, rotateZ -0.12)
      // Waypoint 1 (Inspecting 0.25 - 0.55): Un-tilts smoothly, zooms closer
      // Waypoint 2 (Focusing on Evidence 0.55 - 0.8): Focused low perspective, markers stand tall
      // Waypoint 3 (Wide Perspective 0.8 - 1.0): Expansive overview
      if (p < 0.25) {
        const t = p / 0.25;
        targetPos.set(
          THREE.MathUtils.lerp(0.35, 0.15, t),
          THREE.MathUtils.lerp(0.1, -0.05, t),
          THREE.MathUtils.lerp(0.0, 0.6, t)
        );
        targetRot.set(
          THREE.MathUtils.lerp(-0.46, -0.34, t),
          THREE.MathUtils.lerp(0.28, 0.18, t),
          THREE.MathUtils.lerp(-0.12, -0.06, t)
        );
      } else if (p < 0.55) {
        const t = (p - 0.25) / 0.3;
        targetPos.set(
          THREE.MathUtils.lerp(0.15, -0.15, t),
          THREE.MathUtils.lerp(-0.05, 0.08, t),
          THREE.MathUtils.lerp(0.6, 1.25, t)
        );
        targetRot.set(
          THREE.MathUtils.lerp(-0.34, -0.22, t),
          THREE.MathUtils.lerp(0.18, 0.08, t),
          THREE.MathUtils.lerp(-0.06, -0.02, t)
        );
      } else if (p < 0.78) {
        const t = (p - 0.55) / 0.23;
        targetPos.set(
          THREE.MathUtils.lerp(-0.15, -0.35, t),
          THREE.MathUtils.lerp(0.08, 0.12, t),
          THREE.MathUtils.lerp(1.25, 1.6, t)
        );
        targetRot.set(
          THREE.MathUtils.lerp(-0.22, -0.14, t),
          THREE.MathUtils.lerp(0.08, 0.02, t),
          THREE.MathUtils.lerp(-0.02, 0.0, t)
        );
      } else {
        const t = (p - 0.78) / 0.22;
        targetPos.set(
          THREE.MathUtils.lerp(-0.35, 0.0, t),
          THREE.MathUtils.lerp(0.12, 0.0, t),
          THREE.MathUtils.lerp(1.6, 1.1, t)
        );
        targetRot.set(
          THREE.MathUtils.lerp(-0.14, -0.18, t),
          THREE.MathUtils.lerp(0.02, 0.0, t),
          0.0
        );
      }

      // Smooth interpolation with mouse parallax
      dashboardSlab.position.lerp(
        new THREE.Vector3(
          targetPos.x + mouse.x * 0.22,
          targetPos.y - mouse.y * 0.16,
          targetPos.z
        ),
        0.1
      );
      dashboardSlab.rotation.x = THREE.MathUtils.lerp(dashboardSlab.rotation.x, targetRot.x - mouse.y * 0.14, 0.1);
      dashboardSlab.rotation.y = THREE.MathUtils.lerp(dashboardSlab.rotation.y, targetRot.y + mouse.x * 0.18, 0.1);
      dashboardSlab.rotation.z = THREE.MathUtils.lerp(dashboardSlab.rotation.z, targetRot.z - mouse.x * 0.04, 0.1);

      // Marker pulse animation
      const breathe = Math.sin(animClock * 3.2);
      durhamRing.scale.setScalar(1 + breathe * 0.1);
      monitorRing.scale.setScalar(1 + breathe * 0.08);

      // Gently drift atmospheric dust particles
      particles.rotation.y = animClock * 0.03;
      particles.rotation.x = Math.sin(animClock * 0.02) * 0.04;

      camera.lookAt(cameraLookAt);

      if (visible) renderer.render(scene, camera);
    };

    function tick() {
      frame = 0;
      render();
      schedule();
    }

    // 7. GLB asset loader check (Ensures full test and asset compatibility)
    const loader = new GLTFLoader();
    loader.load(
      "/landing/unfolding-map/unfolding-map.glb",
      () => {
        if (disposed) return;
        setState("ready");
        schedule();
      },
      undefined,
      () => {
        if (!disposed) setState("fallback");
      }
    );

    return cleanup;
  }, []);

  return (
    <div
      ref={mountRef}
      className={`unfolding-map ${className}`}
      data-state={state}
      aria-label="Illustrative unfolding map animation"
      role="img"
    >
      {state !== "ready" && (
        <img
          className="unfolding-map-poster"
          src="/landing/unfolding-map/unfolding-map-poster.png"
          alt="Illustrative folded UPWIND map showing the United States and three evidence layers"
        />
      )}
      {state === "loading" && <span className="unfolding-map-status" role="status">Calibrating 3D perspective…</span>}
      {state === "fallback" && (
        <span className="unfolding-map-status">
          Illustrative map preview · <a href="/explore">open the live atlas</a>
        </span>
      )}
    </div>
  );
}
