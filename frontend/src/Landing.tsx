import { useEffect, useState } from "react";
import { ArrowDownRight, ArrowRight, ArrowUpRight, Map, Wind } from "lucide-react";
import CoverageEvidence from "./CoverageEvidence";
import "./landing.css";

const story = [
  { title: "Modeled estimates", description: "Historical annual PM2.5 estimates are assigned to Census place points from the nearest eligible monitor.", image: "/landing/quality-recovery/place.webp", alt: "Current National Explorer map centered on Durham with the estimates layer" },
  { title: "Monitor measurements", description: "Read annual summaries recorded at EPA monitoring sites as measurements from physical locations.", image: "/landing/quality-recovery/monitors.webp", alt: "Current National Explorer map showing EPA monitor sites" },
  { title: "Emissions inventory", description: "Inspect nearby EPA inventory records separately; proximity does not identify a contribution.", image: "/landing/quality-recovery/sources.webp", alt: "Current National Explorer map showing EPA emissions inventory records" },
  { title: "Place-based comparison", description: "Search a place, then compare these distinct records with their dates, units, and limitations in view.", image: "/landing/quality-recovery/overview.webp", alt: "Current National Explorer map showing national place estimates" },
];

function StorySection() {
  const [active, setActive] = useState(0);
  useEffect(() => {
    const steps = [...document.querySelectorAll<HTMLElement>("[data-story-step]")];
    let frame = 0;
    const updateActiveStep = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const readingLine = window.innerHeight * 0.55;
        const nearest = steps
          .map((step) => ({ step, rect: step.getBoundingClientRect() }))
          .filter(({ rect }) => rect.bottom > 0 && rect.top < window.innerHeight)
          .sort((a, b) =>
            Math.abs(a.rect.top + a.rect.height / 2 - readingLine) -
            Math.abs(b.rect.top + b.rect.height / 2 - readingLine),
          )[0];
        if (nearest) setActive(Number(nearest.step.dataset.storyStep));
      });
    };
    updateActiveStep();
    window.addEventListener("scroll", updateActiveStep, { passive: true });
    window.addEventListener("resize", updateActiveStep);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", updateActiveStep);
      window.removeEventListener("resize", updateActiveStep);
    };
  }, []);
  return <section className="story-section" aria-labelledby="story-heading">
    <div className="landing-shell story-layout">
      <div className="story-copy"><p className="landing-eyebrow">One atlas, distinct evidence</p><h2 id="story-heading">Read the record in context.</h2>
        {story.map((item, index) => <article className={`story-step${active === index ? " is-active" : ""}`} data-story-step={index} key={item.title}>
          <span className="story-step-index">0{index + 1}</span><div><h3>{item.title}</h3><p>{item.description}</p></div>
        </article>)}
      </div>
      <div className="story-visual" aria-live="polite" aria-atomic="true">
        <div className="story-visual-frame"><img key={active} src={story[active].image} alt={story[active].alt} /><div className="story-image-label"><span>{story[active].title}</span><span>STATIC PRODUCT PREVIEW</span></div></div>
        <p className="story-caption">Illustrative views from the National Explorer. Open the atlas to use the live map.</p>
      </div>
    </div>
  </section>;
}

export default function Landing() {
  return <main className="landing-page">
    <a className="landing-skip-link" href="#main-content">Skip to content</a>
    <header className="landing-header"><div className="landing-header-inner">
      <a className="wordmark" href="/" aria-label="UPWIND home"><span className="atlas-mark"><Wind size={16} /></span><span><b>UPWIND</b><small>PUBLIC AIR ATLAS</small></span></a>
      <nav aria-label="Main navigation"><a href="/methodology">Method</a><a className="header-map-link" href="/explore">Open atlas <ArrowUpRight size={14} /></a></nav>
    </div></header>
    <div id="main-content">
      <section className="landing-hero landing-shell" aria-labelledby="landing-title">
        <div className="hero-copy-block"><p className="landing-eyebrow">A public atlas of historical air quality</p><h1 id="landing-title">Explore America’s air quality, place by place.</h1><p className="landing-deck">Compare modeled annual estimates, EPA monitor measurements, and nearby emissions inventory records across U.S. places.</p>
          <div className="hero-actions"><a className="button button-primary" href="/explore">Open the atlas <ArrowRight size={16} /></a><a className="button button-secondary" href="/methodology">Read the method</a></div>
        </div>
        <figure className="atlas-preview"><div className="preview-frame"><div className="preview-toolbar"><span><Map size={14} /> National Explorer</span><span>Current map · estimates</span></div><img src="/landing/quality-recovery/overview.webp" alt="Current high-resolution map preview of modeled annual PM2.5 estimates in the UPWIND National Explorer" /></div><figcaption>Current National Explorer map · modeled annual PM2.5 estimates, 2024.</figcaption></figure>
        <a className="hero-scroll-cue" href="#atlas-story"><span>See how the atlas works</span><ArrowDownRight size={15} /></a>
      </section>
      <div id="atlas-story"><StorySection /></div>
      <CoverageEvidence />
      <section className="final-cta"><div className="landing-shell final-cta-inner"><div><p className="landing-eyebrow">Explore a place</p><h2>Start with a place.</h2><p>Open the atlas to search, compare evidence, and inspect the limits behind each record.</p></div><div className="example-places" aria-label="Example places"><a href="/explore?place=3719000">Durham <ArrowUpRight size={13} /></a><a href="/explore?place=3755000">Raleigh <ArrowUpRight size={13} /></a><a href="/explore?place=3712000">Charlotte <ArrowUpRight size={13} /></a></div><a className="button button-primary" href="/explore">Open the atlas <ArrowRight size={16} /></a></div></section>
    </div>
    <footer className="landing-footer"><span>UPWIND · Public Air Atlas</span><span>Historical public evidence · Not live air quality</span><a href="/methodology">Methodology and data sources <ArrowUpRight size={13} /></a></footer>
  </main>;
}
