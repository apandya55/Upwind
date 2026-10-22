import { useEffect, useRef } from "react";
import "./story-scene.css";

const clamp = (value: number) => Math.max(0, Math.min(1, value));
const range = (progress: number, start: number, end: number) => clamp((progress - start) / (end - start));

/** A single scroll-driven illustration, with a native-scroll static layout on small and reduced-motion screens. */
export default function StoryScene() {
  const sceneRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const compact = window.matchMedia("(max-width: 760px)");
    let frame = 0;
    const update = () => {
      frame = 0;
      if (reduceMotion.matches || compact.matches) {
        scene.style.setProperty("--story-progress", "0");
        scene.style.setProperty("--wind", "1");
        scene.style.setProperty("--wind-caption", "1");
        scene.style.setProperty("--land", "1");
        scene.style.setProperty("--car", "1");
        scene.style.setProperty("--plane", "1");
        scene.style.setProperty("--car-caption", "1");
        scene.style.setProperty("--plane-caption", "1");
        scene.style.setProperty("--evidence", "1");
        return;
      }
      const rect = scene.getBoundingClientRect();
      const progress = clamp(-rect.top / Math.max(1, rect.height - window.innerHeight));
      scene.style.setProperty("--story-progress", `${progress}`);
      scene.style.setProperty("--wind", `${1 - range(progress, 0.15, 0.4) * 0.42}`);
      scene.style.setProperty("--wind-caption", `${1 - range(progress, 0.16, 0.23)}`);
      scene.style.setProperty("--land", `${range(progress, 0.15, 0.35) * (1 - range(progress, 0.7, 0.86))}`);
      scene.style.setProperty("--car", `${range(progress, 0.35, 0.48) * (1 - range(progress, 0.62, 0.76))}`);
      scene.style.setProperty("--plane", `${range(progress, 0.54, 0.72) * (1 - range(progress, 0.82, 0.92))}`);
      scene.style.setProperty("--car-caption", `${range(progress, 0.35, 0.46) * (1 - range(progress, 0.58, 0.64))}`);
      scene.style.setProperty("--plane-caption", `${range(progress, 0.62, 0.74) * (1 - range(progress, 0.82, 0.88))}`);
      scene.style.setProperty("--evidence", `${range(progress, 0.8, 0.94)}`);
    };
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(update); };
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    reduceMotion.addEventListener("change", onScroll);
    compact.addEventListener("change", onScroll);
    update();
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      reduceMotion.removeEventListener("change", onScroll);
      compact.removeEventListener("change", onScroll);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);

  return <section className="continuous-story" id="story" ref={sceneRef} aria-label="How air context leads to geographic evidence">
    <div className="continuous-story__sticky">
      <div className="continuous-story__art" aria-hidden="true">
        <svg className="continuous-story__drawing" viewBox="0 0 1200 700" preserveAspectRatio="xMidYMid meet">
          <defs>
            <linearGradient id="story-sky" x2="0" y2="1"><stop stopColor="#eaf5f2"/><stop offset="1" stopColor="#d5e9e5"/></linearGradient>
            <linearGradient id="story-road" x2="0" y2="1"><stop stopColor="#7d9694"/><stop offset="1" stopColor="#536f70"/></linearGradient>
          </defs>
          <path fill="url(#story-sky)" d="M0 0h1200v700H0z"/>
          <g className="scene-wind" fill="none" stroke="#4b9297" strokeWidth="3" strokeLinecap="round">
            <path d="M555 135c75-45 145 45 245-10s210-30 460-70"/><path d="M525 200c95-40 175 45 285 0s215-50 450-24"/><path d="M565 275c75-38 170 15 245-10s250-55 460-25"/>
            <path d="M595 112l21 16-25 11M800 185l20 15-25 11" strokeWidth="2"/>
          </g>
          <g className="scene-landscape">
            <path fill="#bdd7ca" d="M0 390q150-125 300-30t320-20q155-95 300 10t280-20v370H0z"/>
            <path fill="#a1c6b4" d="M0 462q195-125 355-35t335-16q202-85 510 8v281H0z"/>
            <g transform="translate(202 245)"><path fill="#8b684e" d="M43 178h24l8 88H37z"/><path fill="#58866c" d="M18 100q-26-43 11-65-5-57 44-56 38-43 71-3 52-6 52 42 47 35 8 72 19 43-23 61H42q-52-12-24-51Z"/><path fill="#79a785" d="M35 87q-15-37 18-51 11-39 45-27 33-30 55 6 37-2 38 33 29 24 0 49-8 27-41 31H59q-37-7-24-41Z" opacity=".72"/></g>
            <path d="M0 537q180-80 360-34t363 17q230 25 477-18" fill="none" stroke="#e5eee2" strokeWidth="13"/>
          </g>
          <g className="scene-road">
            <path d="M-100 675q295-206 586-163t807-170" fill="none" stroke="url(#story-road)" strokeWidth="92"/>
            <path d="M-100 675q295-206 586-163t807-170" fill="none" stroke="#f2e9cb" strokeWidth="4" strokeDasharray="32 31"/>
          </g>
          <g className="scene-car" transform="translate(535 474)">
            <g className="scene-wheel"><circle cx="55" cy="65" r="22" fill="#203e43"/><circle cx="55" cy="65" r="9" fill="#c5d1c9"/></g>
            <g className="scene-wheel scene-wheel--rear"><circle cx="174" cy="65" r="22" fill="#203e43"/><circle cx="174" cy="65" r="9" fill="#c5d1c9"/></g>
            <path fill="#d18458" stroke="#8e573c" strokeWidth="4" d="M15 53l13-28q9-15 27-17l40-3 34 29 38 4q19 3 22 20v13H10V61q0-7 5-8Z"/>
            <path fill="#d9eee8" d="M68 14l29-3 25 22H50z"/><path fill="#d9eee8" d="M105 11h8l26 23h-14z"/>
          </g>
          <g className="scene-aircraft" transform="translate(574 210)">
            <path fill="#f4f6ee" stroke="#3c777e" strokeWidth="4" strokeLinejoin="round" d="M-5 35 130 20l90-76 22 2-36 76 198 3 26 14-224 20-72 85-20-1 25-83-121-8z"/>
            <path fill="#8ab8b6" d="M17 35h287l-8 8-223 18z" opacity=".7"/>
          </g>
        </svg>
        <div className="scene-caption scene-caption--wind">Air moves across a landscape</div>
        <div className="scene-caption scene-caption--car">Nearby activity shares the same place</div>
        <div className="scene-caption scene-caption--plane">Some context travels farther</div>
      </div>
      <div className="continuous-story__evidence">
        <div className="evidence-image"><img src="/landing/explorer-overview.png" alt="UPWIND Explorer map with historical air quality estimates and evidence controls"/><span>UPWIND EXPLORER · HISTORICAL EVIDENCE</span></div>
        <div className="evidence-copy"><p>GEOGRAPHIC EVIDENCE</p><h2>Explore what is measured.<br/>Inspect what is nearby.</h2><a href="/explore">Explore the map <span aria-hidden="true">→</span></a></div>
      </div>
      <div className="continuous-story__intro"><p>ONE CONNECTED STORY</p><h2>Follow the air.<br/>Then inspect the evidence.</h2></div>
    </div>
    <div className="continuous-story__sr" aria-live="off"><h2>Air moves across a landscape</h2><p>Nearby activity shares the same place. Some context travels farther. Explore what is measured and inspect what is nearby in the UPWIND Explorer.</p></div>
  </section>;
}
