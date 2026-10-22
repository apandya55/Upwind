import { ArrowLeft, ArrowRight, Check, Database, Download, FileText, MapPin, ShieldCheck } from "lucide-react";
import "./local.css";

const steps = [
  { number: "01", title: "Prepare a CSV", text: "Use the template for PM2.5 readings. Keep the original file and record instrument, method, and quality notes alongside your study." },
  { number: "02", title: "Import and review", text: "Open the workspace, create an investigation, and choose Import data. Map columns, choose a timezone for timestamps without offsets, then review accepted, invalid, and flagged rows." },
  { number: "03", title: "Explore locally", text: "Inspect station locations, readings, and the timeline. Export a private archive or evidence report when you are ready." },
];

export default function LocalPage() {
  return (
    <main className="local-page">
      <nav className="local-nav" aria-label="UPWIND navigation">
        <a className="local-wordmark" href="/" aria-label="UPWIND home">UP<span>wind</span></a>
        <a className="local-nav-link" href="/explore"><ArrowLeft size={15} /> Use the public map</a>
      </nav>
      <section className="local-hero">
        <span className="local-kicker">YOUR DATA STAYS ON YOUR MACHINE</span>
        <h1>Bring local readings into view.</h1>
        <p>Use the workspace to inspect compatible PM2.5 sensor records, station locations, and time patterns. Imports are processed by the local app and saved in its local database.</p>
        <div className="local-actions">
          <a className="local-primary" href="/workspace"><MapPin size={16} /> Open local workspace <ArrowRight size={15} /></a>
          <a className="local-secondary" href="/local/sensor-template.csv" download><Download size={15} /> CSV template</a>
        </div>
        <p className="local-note"><ShieldCheck size={14} /> Files are sent only to the local UPWIND API. No sensor data are sent to map or data providers.</p>
      </section>

      <section className="local-workflow" aria-label="How to import local data">
        <div className="local-section-heading"><span>01 — 03</span><h2>A clear path from file to evidence.</h2></div>
        <div className="local-steps">{steps.map((step) => <article key={step.number}><span>{step.number}</span><h3>{step.title}</h3><p>{step.text}</p></article>)}</div>
      </section>

      <section className="local-inputs">
        <div><span className="local-kicker">INPUTS</span><h2>Start with the essentials.</h2><p>One row per station reading. Use decimal latitude/longitude and PM2.5 concentration in µg/m³. Timestamps should include a UTC offset; otherwise select the correct IANA timezone during import.</p></div>
        <div className="local-input-card"><h3><Check size={16}/> Required columns</h3><code>sensor_id · timestamp · latitude · longitude · pm25_ug_m3</code><p>Optional supported fields: <code>uncertainty_ug_m3</code>, <code>humidity_percent</code>, and <code>temperature_c</code>. The importer preserves the original CSV and flags duplicate or out-of-order readings for review.</p></div>
      </section>

      <section className="local-example">
        <div><span className="local-kicker">TRY THE FLOW</span><h2>Practice with a labeled example.</h2><p>This small fixture is synthetic, generated for software demonstrations, and is not an environmental observation. Its <code>origin=synthetic</code> label follows it into exports.</p></div>
        <a className="local-secondary" href="/local/synthetic-measurements.csv" download><FileText size={15}/> Download synthetic CSV</a>
      </section>

      <section className="local-install">
        <div><span className="local-kicker">RUN IT LOCALLY</span><h2>Install the repository.</h2><p>Tested setup: Python 3.12+, Node 22.12+ (Node 24.19 verified), and npm on macOS/Linux. The configured repository remote responds and exposes its main branch.</p><a href="https://github.com/apandya55/Upwind" target="_blank" rel="noreferrer">github.com/apandya55/Upwind <ArrowRight size={14}/></a></div>
        <pre aria-label="Local installation commands"><code>git clone https://github.com/apandya55/Upwind.git
cd Upwind
bash scripts/setup.sh
bash scripts/dev.sh</code></pre>
        <p className="local-install-foot"><Database size={15}/> Then open <strong>http://127.0.0.1:5173</strong>. Analysis and saved imports run locally. The national map and basemap context require internet; local CSV inspection does not require an external account or paid key.</p>
      </section>

      <footer className="local-footnote">Local data remain on this machine, but local storage is not encrypted. Treat JSON archives as sensitive: they can contain exact coordinates and raw imported files. Source investigation is conditional research, not proof of emissions responsibility.</footer>
    </main>
  );
}
