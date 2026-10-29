import { ArrowLeft, ArrowUpRight, Compass } from "lucide-react";
import Navbar from "./Navbar";
import Footer from "./Footer";
import "./methodology.css";

const sources = [
  ["Census Gazetteer", "2024", "Searchable place GEOIDs and internal-point coordinates across the contiguous United States."],
  ["EPA Air Quality System (AQS)", "2018–2025", "Annual PM2.5 summaries at physical monitoring sites; 2025 summaries are provisional."],
  ["EPA National Emissions Inventory (NEI)", "2023", "Facility PM2.5-PRI inventory records in source units (tons/year)."],
  ["PRISM Climate Group", "Annual grids evaluated", "Annual mean temperature was tested as a candidate covariate; it is not part of the deployed place-estimation method."],
];

export default function MethodologyPage() {
  return (
    <main className="method-page">
      <Navbar active="methodology" />

      <article className="method-article">
        <div className="method-topline">
          <a href="/"><ArrowLeft size={14} /> Back to home</a>
          <a className="method-open-link" href="/explore">Open atlas <ArrowUpRight size={14} /></a>
        </div>

        <p className="method-kicker">Technical reference</p>
        <h1>Method, evidence, and limits.</h1>
        <p className="method-intro">
          UPWIND uses three public datasets from the EPA and Census Bureau. This technical brief summarizes how place-point
          estimates are calculated, how empirical error intervals are derived, and what these records can and cannot support.
        </p>

        <section className="method-release" aria-label="Release summary">
          <div className="method-release-header">
            <div>
              <span className="method-label">NATIONAL EXPLORER 0.3.0</span>
              <h2>Nearest-monitor annual PM2.5</h2>
            </div>
            <div className="method-release-identifiers">
              <div>Model: <code>upwind-nearest-monitor-annual-pm25-0.3.0</code></div>
              <div>Protocol: <code>UW-NATIONAL-SPATIAL-2026-04</code></div>
            </div>
          </div>
          <div className="method-release-stats">
            <div className="release-stat-item">
              <span className="release-stat-label">Searchable places</span>
              <strong className="release-stat-value">32,333</strong>
            </div>
            <div className="release-stat-item">
              <span className="release-stat-label">2024 estimates</span>
              <strong className="release-stat-value">31,523</strong>
            </div>
            <div className="release-stat-item">
              <span className="release-stat-label">Eligible monitor sites</span>
              <strong className="release-stat-value">894</strong>
            </div>
          </div>
        </section>

        {/* Section 01: Assignment Pipeline */}
        <section className="method-section" id="assignment">
          <div className="method-section-heading">
            <span className="method-label">How a place estimate is assigned</span>
            <h2>From annual monitor summaries to a place point.</h2>
          </div>

          <div
            className="method-pipeline"
            role="img"
            aria-label="Eligible 2024 EPA monitor summaries are matched to Census Gazetteer place points by nearest eligible site, then reported as historical annual PM2.5 place estimates."
          >
            <div className="method-step">
              <span className="method-step-tag">INPUT DATA</span>
              <strong>Eligible EPA AQS summaries</strong>
              <small>2024 · parameter 88101 · µg/m³</small>
            </div>
            <div className="method-pipeline-arrow" aria-hidden="true">→</div>
            <div className="method-step">
              <span className="method-step-tag">SPATIAL MATCH</span>
              <strong>Nearest eligible monitor</strong>
              <small>At each Census internal point</small>
            </div>
            <div className="method-pipeline-arrow" aria-hidden="true">→</div>
            <div className="method-step">
              <span className="method-step-tag">OUTPUT VALUE</span>
              <strong>Place-point estimate</strong>
              <small>Historical annual PM2.5</small>
            </div>
          </div>

          <p className="method-note">
            A place receives the annual summary from its nearest eligible physical monitor. There are no learned
            pollution covariates in this deployed method. The point is not a citywide, polygon, or population-weighted
            average. 810 searchable places are withheld by the contiguous-U.S. domain and monitor-distance support rule.
          </p>
        </section>

        {/* Section 02: Evidence Comparison Matrix */}
        <section className="method-section" id="evidence">
          <div className="method-section-heading">
            <span className="method-label">Evidence layers</span>
            <h2>Each layer answers a different question.</h2>
          </div>

          <div className="method-table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col">Layer</th>
                  <th scope="col">What it contains</th>
                  <th scope="col">Unit / location</th>
                  <th scope="col">Interpretation</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th scope="row">Estimates</th>
                  <td>Nearest eligible monitor’s annual PM2.5 summary assigned to Census place points</td>
                  <td>µg/m³ · place point</td>
                  <td>Historical model estimate, not a local measurement</td>
                </tr>
                <tr>
                  <th scope="row">Monitors</th>
                  <td>EPA AQS annual summaries from physical sites</td>
                  <td>µg/m³ · station site</td>
                  <td>Observed at the monitor; not every location in a place</td>
                </tr>
                <tr>
                  <th scope="row">Sources</th>
                  <td>EPA NEI facility PM2.5-PRI inventory records</td>
                  <td>Source units (tons) · facility</td>
                  <td>Inventory record; proximity does not establish contribution</td>
                </tr>
              </tbody>
            </table>
          </div>

          <p className="method-note">
            AQS selection retains parameter, metric, units, completeness, event treatment, certification, and selected
            colocated POC provenance. One ambient annual summary is selected per POC, preferring “Events Included” when
            present, otherwise “No Events.” Selected colocated POCs are combined once per physical site.
          </p>
        </section>

        {/* Section 03: Model Selection & Empirical Validation */}
        <section className="method-section" id="validation">
          <div className="method-section-heading">
            <span className="method-label">Model choice and validation</span>
            <h2>Why nearest monitor remains in the release.</h2>
          </div>

          <div className="validation-summary">
            <p className="validation-narrative">
              The fixed 150 km Gaussian-kernel ridge candidate and the Gaussian candidate with a linear PRISM
              annual-mean-temperature term were compared with the nearest-monitor method using matched sites and spatial
              folds. Neither candidate met the protocol requirement of at least four of five fold wins in both years, so
              nearest monitor remains deployed.
            </p>
            <div className="validation-metrics-table" aria-label="Validation fold comparison">
              <div className="validation-metric-row">
                <span>2024 · matched PRISM</span>
                <strong>5/5 folds</strong>
                <small>Development evidence</small>
              </div>
              <div className="validation-metric-row">
                <span>2025 · provisional</span>
                <strong>3/5 folds</strong>
                <small>Below the 4/5 rule</small>
              </div>
            </div>
          </div>

          <p className="method-note">
            The already-inspected folds are development evidence, not a fresh final evaluation. No untouched final set
            remains for this release; no final accuracy claim is made. The deployed ±4.123 µg/m³ band is the 90th percentile
            of corrected spatial out-of-fold nearest-monitor absolute residuals; it is not a local guarantee or a Bayesian
            credible interval.
          </p>
        </section>

        {/* Section 04: Scientific Limits */}
        <section className="method-section" id="limits">
          <div className="method-section-heading">
            <span className="method-label">Limits and scope</span>
            <h2>Use the records within their scope.</h2>
          </div>

          <ul className="method-limits-grid">
            <li>Historical annual data, not live conditions, daily changes, or a forecast.</li>
            <li>Place points do not represent all locations or personal exposure within a place.</li>
            <li>No independent between-monitor field validation or local calibration is established.</li>
            <li>Nearby inventory records do not establish source attribution or responsibility.</li>
            <li>2025 AQS summaries are provisional; 810 places do not have supported 2024 estimates.</li>
          </ul>
        </section>

        {/* Section 05: Data Sources */}
        <section className="method-section" id="sources">
          <div className="method-section-heading">
            <span className="method-label">Data sources</span>
            <h2>Public records in this release.</h2>
          </div>

          <div className="source-list">
            {sources.map(([name, period, description]) => (
              <div className="source-row" key={name}>
                <strong>{name}</strong>
                <span>{period}</span>
                <p>{description}</p>
              </div>
            ))}
          </div>

          <div className="source-links">
            <a href="https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html" target="_blank" rel="noreferrer">
              Census Gazetteer <ArrowUpRight size={12} />
            </a>
            <a href="https://www.epa.gov/aqs" target="_blank" rel="noreferrer">
              EPA AQS <ArrowUpRight size={12} />
            </a>
            <a href="https://www.epa.gov/air-emissions-inventories/2023-national-emissions-inventory-nei-data" target="_blank" rel="noreferrer">
              EPA 2023 NEI <ArrowUpRight size={12} />
            </a>
            <a href="https://prism.oregonstate.edu/" target="_blank" rel="noreferrer">
              PRISM Climate Group <ArrowUpRight size={12} />
            </a>
          </div>
        </section>

        <div className="method-last-cta">
          <div>
            <h3>Questions about what the atlas shows?</h3>
            <p>Search a place and inspect the evidence behind it.</p>
          </div>
          <a href="/explore">
            <Compass size={15} /> Open the atlas
          </a>
        </div>
      </article>

      <Footer />
    </main>
  );
}
