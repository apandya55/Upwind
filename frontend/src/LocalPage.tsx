import { ArrowUpRight, Check, Code, Download, ExternalLink, FileText, Terminal } from "lucide-react";
import Navbar from "./Navbar";
import Footer from "./Footer";
import "./local.css";

const explorerBuild = import.meta.env.VITE_APP_SURFACE === "explorer";

export default function LocalPage() {
  if (explorerBuild) {
    return (
      <main className="local-page">
        <Navbar active="run" />
        <section className="local-hero">
          <span className="local-kicker">LOCAL RESEARCH SOFTWARE</span>
          <h1>Run the engine on your own computer.</h1>
          <p>
            UPWIND's experimental engine is for local analysis of user-supplied measurements and weather data. This public
            Explorer does not accept uploads. Local files stay on your machine when you run the research workspace yourself.
          </p>
          <div className="local-actions">
            <a className="local-primary" href="https://github.com/apandya55/Upwind" target="_blank" rel="noreferrer">
              <Code size={16} /> View source <ArrowUpRight size={14} />
            </a>
            <a className="local-secondary" href="/">Explore national data <ArrowUpRight size={14} /></a>
          </div>
          <p className="local-note">Research software · synthetic evaluation only · no field accuracy claim</p>
        </section>
        <section className="local-workflow" aria-label="Local setup">
          <div className="local-section-heading"><span>SETUP</span><h2>Start from the source repository.</h2></div>
          <pre><code>{`git clone https://github.com/apandya55/Upwind.git\ncd Upwind\nbash scripts/setup.sh\nbash scripts/dev.sh`}</code></pre>
          <p>Requires Python 3.12+ and Node 22.12+. Read the model, data handling, and limitations in the repository documentation before interpreting results.</p>
          <p><a href="https://github.com/apandya55/Upwind/blob/main/docs/SCIENCE.md" target="_blank" rel="noreferrer">Scientific scope and limitations <ArrowUpRight size={14} /></a></p>
        </section>
        <Footer />
      </main>
    );
  }
  return (
    <main className="local-page">
      <Navbar active="run" />

      {/* Hero Section */}
      <section className="local-hero">
        <span className="local-kicker">DEVELOPER TUTORIAL · RUN LOCALLY</span>
        <h1>Run UPWIND and the model on your own machine.</h1>
        <p>
          The source code and analysis steps are available to inspect. You don't need cloud credentials or API tokens to run
          the local workflow. You can clone the repository, download the EPA and Census source files, rebuild the data,
          and run the interactive map right on your laptop.
        </p>
        <div className="local-actions">
          <a
            className="local-primary"
            href="https://github.com/apandya55/Upwind"
            target="_blank"
            rel="noreferrer"
          >
            <Code size={16} /> View on GitHub <ArrowUpRight size={14} />
          </a>
          <a className="local-secondary" href="/explore">
            Explore the map <ArrowUpRight size={14} />
          </a>
          <a className="local-secondary" href="/local/sensor-template.csv" download>
            <Download size={15} /> CSV template
          </a>
          {/* Discreet link for research workspace */}
          <a className="local-secondary" href="/workspace" style={{ fontSize: "12px" }}>
            Open local workspace <ArrowUpRight size={13} />
          </a>
        </div>
        <p className="local-note">
          Tested on macOS and Linux with Python 3.12+ and Node 22+.
        </p>
      </section>

      {/* Step by Step Guide */}
      <section className="local-workflow" aria-label="Step by step tutorial">
        <div className="local-section-heading">
          <span>TUTORIAL</span>
          <h2>How to download data, fit the model, and run the app.</h2>
        </div>

        <div className="local-steps">
          <article>
            <span>01 · REPOSITORY</span>
            <h3>Clone and install</h3>
            <p>Clone the source tree from GitHub and set up Python and Node virtual environments.</p>
            <pre style={{ marginTop: "12px" }}>
              <code>{`git clone https://github.com/apandya55/Upwind.git
cd Upwind
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && cd ..`}</code>
            </pre>
          </article>

          <article>
            <span>02 · DATASETS</span>
            <h3>Download raw records</h3>
            <p>
              Fetch public Census Gazetteer 2024 centroids, EPA AQS monitor summaries, and NEI emissions records into your local <code>data/</code> folder.
            </p>
            <pre style={{ marginTop: "12px" }}>
              <code>{`# Download and compile national data:
python scripts/build_national_dataset.py \\
  --start-year 2018 \\
  --end-year 2025`}</code>
            </pre>
          </article>

          <article>
            <span>03 · MODEL</span>
            <h3>Fit and evaluate</h3>
            <p>
              Execute spatial 5-fold cross-validation on monitor observations and assign point estimates to 32,333 Census places.
            </p>
            <pre style={{ marginTop: "12px" }}>
              <code>{`# Run spatial evaluations:
python scripts/evaluate_national_v2.py
python scripts/evaluate_national_v3.py`}</code>
            </pre>
          </article>
        </div>

        <div style={{ marginTop: "32px", padding: "20px", background: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: "8px" }}>
          <span className="local-kicker">STEP 04 · LOCAL INTERACTIVE MAP</span>
          <h3 style={{ margin: "8px 0 6px", fontSize: "16px", color: "#0F172A" }}>Start the local development server</h3>
          <p style={{ margin: "0 0 14px", fontSize: "13px", color: "#475569", lineHeight: 1.6 }}>
            Run the single startup script to start the local FastAPI server and Vite frontend together. Once running, open{" "}
            <strong>http://localhost:5173</strong> to inspect the map offline.
          </p>
          <pre>
            <code>{`bash scripts/dev.sh`}</code>
          </pre>
        </div>
      </section>

      {/* Bring your own data section (Custom CSVs) */}
      <section className="local-inputs">
        <div>
          <span className="local-kicker">OPTIONAL · SENSOR INGESTION</span>
          <h2>Bring local readings into view.</h2>
          <p>
            If you have local sensor streams (like PurpleAir, Clarity, or custom monitoring hardware), you can format them into a
            standard CSV to inspect them alongside official EPA reference monitors.
          </p>
          <p className="local-note" style={{ margin: "16px 0 0" }}>
            Files are sent only to the local UPWIND API. No sensor data are sent to map or data providers.
          </p>
        </div>
        <div className="local-input-card">
          <h3>
            <Check size={16} /> Required columns
          </h3>
          <code>sensor_id · timestamp · latitude · longitude · pm25_ug_m3</code>
          <p>
            Optional fields: <code>uncertainty_ug_m3</code>, <code>humidity_percent</code>, and <code>temperature_c</code>.
            Timestamps should include a UTC offset (e.g. <code>2024-06-15T14:30:00Z</code>).
          </p>
        </div>
      </section>

      {/* Practice example */}
      <section className="local-example">
        <div>
          <span className="local-kicker">TEST DATA</span>
          <h2>Practice with a labeled example.</h2>
          <p>
            We include a synthetic test fixture with dummy readings to verify CSV formatting and data ingestion scripts. It is
            labeled <code>origin=synthetic</code> so it is never mistaken for physical observations.
          </p>
        </div>
        <a className="local-secondary" href="/local/synthetic-measurements.csv" download>
          <FileText size={15} /> Download synthetic CSV
        </a>
      </section>

      <Footer />
    </main>
  );
}
