import { useEffect } from "react";
import { ArrowDown, ArrowRight, ArrowUpRight, Database, Factory, MapPinned, Wind } from "lucide-react";
import CoverageEvidence from "./CoverageEvidence";
import "./landing.css";

function AtlasMark() {
  return <span className="atlas-mark" aria-hidden="true"><Wind size={17} strokeWidth={1.8} /></span>;
}

export default function Landing() {
  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      const max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      document.documentElement.style.setProperty("--page-progress", String(Math.min(1, window.scrollY / max)));
    };
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(update); };
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    update();
    return () => { window.removeEventListener("scroll", onScroll); window.removeEventListener("resize", onScroll); if (frame) cancelAnimationFrame(frame); };
  }, []);
  return <main className="landing-page">
    <a href="#landing-content" className="landing-skip-link">Skip to content</a>
    <div className="page-progress" aria-hidden="true"><span /></div>
    <header className="landing-header">
      <a href="/" className="wordmark" aria-label="UPWIND public air atlas home"><AtlasMark /><span><b>UPWIND</b><small>PUBLIC AIR ATLAS</small></span></a>
      <nav aria-label="Main navigation"><a href="#method">How to read this map</a><a href="/local">Local sensor data</a><a href="/explore" className="header-map-link">Explore the map <ArrowRight size={15} /></a></nav>
    </header>

    <section className="landing-hero" id="landing-content" aria-labelledby="landing-title">
      <div className="hero-intro">
        <p className="kicker"><span className="kicker-rule" /> A historical air-quality atlas <span className="kicker-year">2024 evidence</span></p>
        <h1 id="landing-title">Explore your<br className="desktop-break"/> community’s air record.</h1>
        <p className="hero-copy">See where annual PM2.5 evidence is available, inspect the monitor and inventory records behind a place, and share a sourced view.</p>
        <div className="hero-cta-wrap">
          <svg className="cta-annotation" viewBox="0 0 164 76" fill="none" aria-hidden="true"><path className="cta-annotation-path" pathLength="1" d="M157 8C124 5 106 12 92 31C77 50 64 62 42 62C30 62 20 58 11 52" /><path className="cta-annotation-head" d="m18 47-8 5 7 7" /></svg>
          <a className="button button-primary" href="/explore">Explore the map <ArrowRight size={16} /></a>
        </div>
        <a className="secondary-action" href="/local">Have your own sensor readings? <span>Use the local workspace <ArrowUpRight size={14} /></span></a>
      </div>

      <figure className="hero-product">
        <div className="hero-map-meta"><span><i /> Historical modeled estimates</span><span>United States · 2024</span></div>
        <a href="/explore" className="hero-map-link" aria-label="Open the UPWIND map explorer">
          <img src="/landing/explorer-overview.png" alt="UPWIND map showing Census place estimates across the contiguous United States, with the map controls and evidence panel visible" loading="eager" decoding="async" fetchPriority="high" />
          <span className="map-open-label">Open the atlas <ArrowUpRight size={14} /></span>
        </a>
        <figcaption><span>PLACE ESTIMATES</span><span>Nearest eligible EPA monitor · point values, not area averages</span></figcaption>
      </figure>
      <a href="#durham" className="hero-scroll"><span>Follow one place through the evidence</span><ArrowDown size={15} /></a>
    </section>

    <section className="durham-story" id="durham" aria-labelledby="durham-title">
      <div className="story-heading">
        <p className="kicker">A place, read carefully <span className="kicker-year">Durham, North Carolina</span></p>
        <h2 id="durham-title">One point.<br />Several kinds of evidence.</h2>
        <p>UPWIND keeps a modeled place estimate, a monitor measurement, and facility inventory records distinct so you can see what each can—and cannot—tell you.</p>
        <a className="text-link" href="/explore">Inspect Durham in the Explorer <ArrowRight size={15} /></a>
      </div>
      <div className="durham-evidence">
        <div className="durham-map-crop">
          <img src="/landing/durham-map-view.png" alt="Focused map view of central North Carolina, with Durham marked among surrounding Census place points" loading="lazy" decoding="async" />
          <span className="map-coordinate-note"><MapPinned size={14} /> Durham · Census Gazetteer point</span>
          <span className="map-attribution">© OpenStreetMap contributors</span>
        </div>
        <div className="evidence-ledger">
          <div className="ledger-head"><span>Durham city · North Carolina</span><span>2024 annual record</span></div>
          <article className="evidence-row estimate-row">
            <span className="evidence-symbol estimate-symbol" aria-hidden="true" />
            <div><p>Place estimate <span>MODELED</span></p><strong>9.71 <small>µg/m³</small></strong><small>PM2.5 · annual · nearest-monitor method</small></div>
            <div className="evidence-side"><b>5.58–13.83</b><small>empirical 90% band</small></div>
          </article>
          <article className="evidence-row monitor-row">
            <span className="evidence-symbol monitor-symbol" aria-hidden="true" />
            <div><p>Supporting monitor <span>MEASURED</span></p><strong>AQS 37-063-0015</strong><small>6.1 km from the Census point</small></div>
            <div className="evidence-side"><small>Observed value is the estimate’s nearest-site input</small></div>
          </article>
          <article className="evidence-row source-row">
            <span className="evidence-symbol source-symbol" aria-hidden="true"><Factory size={14} /></span>
            <div><p>Nearby inventory record <span>EPA NEI · 2023</span></p><strong>103.50 <small>TON / year</small></strong><small>CertainTeed Corporation · 43.3 km</small></div>
            <div className="evidence-side"><small>Inventory emissions are not an ambient measurement</small></div>
          </article>
          <p className="ledger-caveat">This point estimate is not a citywide average, current condition, or evidence that a nearby facility contributed to the monitor reading. The empirical band is not a local guarantee.</p>
        </div>
      </div>
    </section>

    <section className="method-strip" id="method" aria-labelledby="method-title">
      <div className="method-intro"><p className="kicker">Read the record, then its limits</p><h2 id="method-title">A map is a starting point.</h2><p>Every layer carries its own source and date. Place estimates use EPA AQS annual monitor data; the map’s dots are Census Gazetteer points. Nearby EPA inventory entries describe reported emissions—not responsibility.</p><a href="/explore" className="text-link">Read the release methodology <ArrowUpRight size={14} /></a></div>
      <div className="method-lines" aria-label="UPWIND evidence types"><div><i className="method-dot estimate-symbol" /><span><b>Place estimate</b><small>Modeled value · Census point · 2024</small></span></div><div><i className="method-dot monitor-symbol" /><span><b>Monitor record</b><small>Measured at a station · dated annual summary</small></span></div><div><i className="method-dot source-symbol"><Factory size={13} /></i><span><b>Facility inventory</b><small>Reported emissions · source units · 2023</small></span></div></div>
    </section>

    <CoverageEvidence />

    <section className="local-pathway"><div className="local-pathway-mark"><Database size={20} strokeWidth={1.7} /></div><div><p className="kicker">A separate local workflow</p><h2>Bring compatible sensor readings into your own workspace.</h2><p>Upload a PM2.5 CSV to inspect station locations and time patterns. Your imported measurements stay distinct from public monitor records and model estimates.</p></div><a className="button button-secondary" href="/local">Prepare a sensor file <ArrowRight size={15} /></a></section>

    <footer className="landing-footer"><a href="/" className="wordmark wordmark-footer"><AtlasMark /><span><b>UPWIND</b><small>PUBLIC AIR ATLAS</small></span></a><span>Historical evidence · dated, sourced, and limited.</span><nav aria-label="Footer navigation"><a href="/explore">Explore map</a><a href="/local">Local data</a><a href="/workspace">Research workspace</a></nav></footer>
  </main>;
}
