import { useEffect, useRef, type RefObject } from "react";
import { ArrowDown, ArrowRight, Wind } from "lucide-react";

const chapters = [
  { label: "01 / FIND A PLACE", title: "Start with somewhere you know.", body: "Search a city and move from the national view to a dated local estimate.", src: "/assets/explorer-overview.png", alt: "UPWIND national map showing the 2024 modeled-estimate layer" },
  { label: "02 / READ THE ESTIMATE", title: "See the context around a number.", body: "Open a place to read the estimate, its uncertainty, year, and nearby monitoring context.", src: "/assets/explorer-place.png", alt: "UPWIND place detail showing a dated estimate and its uncertainty range" },
  { label: "03 / COMPARE EVIDENCE", title: "Keep reported sources in view.", body: "Show inventory records beside estimates. A nearby facility is context; proximity alone does not show it caused a measurement.", src: "/assets/explorer-sources.png", alt: "UPWIND map with reported inventory locations shown as a distinct layer" },
];

function useScrollMotion(storyRef: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const root = document.documentElement;
    const story = storyRef.current;
    const reduce = matchMedia("(prefers-reduced-motion: reduce)");
    const small = matchMedia("(max-width: 760px)");
    let frame = 0;
    const update = () => {
      frame = 0;
      root.style.setProperty("--hero-shift", `${Math.min(scrollY, innerHeight * 1.5)}px`);
      if (!story || reduce.matches || small.matches) {
        story?.style.setProperty("--story-progress", "0");
        return;
      }
      const rect = story.getBoundingClientRect();
      const progress = Math.max(0, Math.min(1, -rect.top / Math.max(1, rect.height - innerHeight)));
      story.style.setProperty("--story-progress", String(progress));
      story.style.setProperty("--chapter-1", String(Math.max(0, Math.min(1, 1 - progress * 2))));
      story.style.setProperty("--chapter-2", String(Math.max(0, Math.min(1, 1 - Math.abs(progress - 0.5) * 4))));
      story.style.setProperty("--chapter-3", String(Math.max(0, Math.min(1, (progress - 0.5) * 2))));
    };
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(update); };
    addEventListener("scroll", onScroll, { passive: true });
    addEventListener("resize", onScroll);
    reduce.addEventListener("change", onScroll);
    small.addEventListener("change", onScroll);
    update();
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
      if (entry.isIntersecting) { entry.target.classList.add("is-visible"); observer.unobserve(entry.target); }
    }), { threshold: 0.12 });
    document.querySelectorAll("[data-reveal]").forEach((node) => observer.observe(node));
    return () => {
      removeEventListener("scroll", onScroll); removeEventListener("resize", onScroll);
      reduce.removeEventListener("change", onScroll); small.removeEventListener("change", onScroll);
      if (frame) cancelAnimationFrame(frame); observer.disconnect();
    };
  }, [storyRef]);
}

export default function App() {
  const storyRef = useRef<HTMLElement>(null);
  useScrollMotion(storyRef);
  return <main className="site-shell">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <header className="site-header">
      <a className="brand" href="#top" aria-label="UPWIND home"><span className="brand-mark"><Wind size={19}/></span><span>UPWIND<small>PUBLIC AIR ATLAS</small></span></a>
      <nav aria-label="Main navigation"><a href="#approach">How it works</a><a href="#evidence">Evidence</a><a className="nav-cta" href="/explore">Open Explorer <ArrowRight size={15}/></a></nav>
    </header>

    <section className="hero" id="top" aria-labelledby="hero-title">
      <div className="hero-orbit hero-orbit--one" aria-hidden="true"/><div className="hero-orbit hero-orbit--two" aria-hidden="true"/>
      <div className="hero-copy" id="main-content">
        <p className="eyebrow"><span/> A clearer view of local air evidence</p>
        <h1 id="hero-title">Air evidence,<br/><em>within reach.</em></h1>
        <p className="hero-deck">UPWIND helps communities understand local air-quality evidence, inspect nearby reported emissions, and share clear, sourced findings.</p>
        <div className="hero-actions"><a className="button button-primary" href="/explore">Explore the map <ArrowRight size={16}/></a><a className="button button-text" href="/local">Bring local sensor data <ArrowRight size={16}/></a></div>
        <p className="hero-note">Historical evidence · distinct sources · clear limitations</p>
      </div>
      <figure className="hero-figure" data-reveal>
        <div className="hero-image-wrap"><img src="/assets/explorer-overview.png" alt="UPWIND Explorer showing historical estimates across the United States" fetchPriority="high"/><span className="image-index">01 <i/> THE NATIONAL VIEW</span></div>
        <figcaption><span>Explore a dated national estimate</span><span>UNITED STATES · 2024</span></figcaption>
      </figure>
      <a className="scroll-hint" href="#approach"><span>Scroll to explore</span><ArrowDown size={15}/></a>
    </section>

    <section className="intro-band" id="approach" data-reveal>
      <p className="eyebrow">A way into the evidence</p><h2>One place. Different records.<br/><em>Clearer questions.</em></h2>
      <p>Move through estimates, measurements, and reported inventories while keeping their meaning distinct.</p>
    </section>

    <section className="story" ref={storyRef} aria-label="How to explore UPWIND">
      <div className="story-sticky">
        <div className="story-heading"><p className="eyebrow">Explore the layers <span className="story-count">01 — 03</span></p><div className="story-progress"><span/></div></div>
        <div className="story-layout">
          <div className="chapter-copy">{chapters.map((chapter, i) => <article key={chapter.label} className={`chapter chapter-${i + 1}`}><p className="eyebrow">{chapter.label}</p><h3>{chapter.title}</h3><p>{chapter.body}</p></article>)}</div>
          <div className="story-stage" aria-label="Explorer screenshots">
            {chapters.map((chapter, i) => <figure key={chapter.src} className={`story-frame story-frame-${i + 1}`}><img src={chapter.src} alt={chapter.alt} loading="lazy"/><figcaption>{chapter.label}</figcaption></figure>)}
            <div className="stage-index" aria-hidden="true"><span>01</span><i/><span>03</span></div>
          </div>
        </div>
        <div className="story-foot"><span>Keep scrolling to move through the Explorer</span><span>Scroll progress</span></div>
      </div>
    </section>

    <section className="evidence" id="evidence">
      <div className="evidence-heading" data-reveal><p className="eyebrow">Read each layer on its own terms</p><h2>Evidence has<br/><em>different jobs.</em></h2></div>
      <div className="evidence-list">
        <article data-reveal><span className="evidence-number">01</span><div><h3>Modeled estimates</h3><p>Derived values with a stated place, year, method, and uncertainty. They are estimates, not direct observations.</p></div><span className="evidence-type">MODEL</span></article>
        <article data-reveal><span className="evidence-number">02</span><div><h3>Measurements</h3><p>Readings from monitoring instruments, with their own dates, locations, and provenance.</p></div><span className="evidence-type">OBSERVED</span></article>
        <article data-reveal><span className="evidence-number">03</span><div><h3>Inventory records</h3><p>Reported emissions records shown as their own evidence. Location alone does not establish contribution.</p></div><span className="evidence-type">REPORTED</span></article>
      </div>
      <p className="evidence-limit">Coverage varies by place, year, and source. UPWIND does not establish real-world accuracy or causal attribution.</p>
    </section>

    <section className="closing" data-reveal><p className="eyebrow">Start with a question</p><h2>See what’s available<br/>where you live.</h2><div className="hero-actions"><a className="button button-primary" href="/explore">Open the Explorer <ArrowRight size={16}/></a><a className="button button-light" href="/local">Use local data <ArrowRight size={16}/></a></div><span className="closing-mark" aria-hidden="true"><Wind size={28}/></span></section>
    <footer className="site-footer"><a className="brand" href="#top"><span className="brand-mark"><Wind size={17}/></span><span>UPWIND<small>PUBLIC AIR ATLAS</small></span></a><p>Historical evidence, clearly labeled.</p><a href="#top">Back to top ↑</a></footer>
  </main>;
}
