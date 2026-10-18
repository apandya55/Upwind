import { ArrowLeft, ArrowUpRight, Compass, FileText } from "lucide-react";
import Navbar from "./Navbar";
import Footer from "./Footer";
import "./about.css";

const repository = "https://github.com/apandya55/Upwind";

export default function AboutPage() {
  return (
    <main className="about-page">
      <Navbar active="about" />
      <article className="about-container">
        <div className="about-topline">
          <a href="/">
            <ArrowLeft size={14} /> Back to the atlas
          </a>
          <span>National Explorer · release 0.3.0</span>
        </div>

        <header className="about-hero">
          <span className="about-kicker">About UPWIND</span>
          <h1>A public atlas for exploring historical air-quality evidence.</h1>
          <p className="about-hero-lead">
            UPWIND puts annual PM2.5 estimates, measurements from EPA monitoring
            sites, and emissions inventory records on one map. Each layer keeps
            its own meaning and limitations visible.
          </p>
        </header>

        <section
          className="about-spec-sheet"
          aria-labelledby="about-release-title"
        >
          <div className="spec-sheet-header">
            <div>
              <span className="spec-sheet-kicker">Current data release</span>
              <h2 className="spec-sheet-title" id="about-release-title">
                Coverage in the current atlas
              </h2>
            </div>
            <span className="spec-sheet-tag">Built 20 October 2026</span>
          </div>
          <div className="about-index-rows">
            <div className="about-index-row">
              <span className="index-row-title">Searchable Census places</span>
              <div className="index-row-val">
                <span className="spec-highlight">32,333</span>
              </div>
              <p className="index-row-desc">
                2024 Gazetteer GEOIDs and internal-point coordinates. A point
                does not represent an entire place.
              </p>
            </div>
            <div className="about-index-row">
              <span className="index-row-title">Supported 2024 estimates</span>
              <div className="index-row-val">
                <span className="spec-highlight">31,523</span>
              </div>
              <p className="index-row-desc">
                Nearest eligible monitor summaries assigned to supported place
                points; 810 places are withheld.
              </p>
            </div>
            <div className="about-index-row">
              <span className="index-row-title">
                Eligible 2024 monitor sites
              </span>
              <div className="index-row-val">
                <span className="spec-highlight">894</span>
              </div>
              <p className="index-row-desc">
                Physical AQS sites used by the deployed annual PM2.5 method.
              </p>
            </div>
            <div className="about-index-row">
              <span className="index-row-title">2023 inventory records</span>
              <div className="index-row-val">
                <span className="spec-highlight">76,404</span>
              </div>
              <p className="index-row-desc">
                Mapped NEI facility records with coordinates. Inventory values
                are not ambient measurements.
              </p>
            </div>
          </div>
        </section>

        <section className="about-section">
          <div className="about-section-header">
            <span className="about-kicker">How to read it</span>
            <h2>Three records, three different things.</h2>
          </div>
          <div className="about-rules-list">
            <article className="about-rule-item">
              <div className="rule-body">
                <h3>Place estimates</h3>
                <p>
                  The release assigns the nearest eligible 2024 monitor summary
                  to a Census Gazetteer internal point. It is a historical
                  estimate at that point, not a citywide or neighborhood
                  average.
                </p>
              </div>
            </article>
            <article className="about-rule-item">
              <div className="rule-body">
                <h3>Monitor measurements</h3>
                <p>
                  Annual AQS summaries describe readings at physical sites. A
                  monitor reading does not describe every location around the
                  station.
                </p>
              </div>
            </article>
            <article className="about-rule-item">
              <div className="rule-body">
                <h3>Emissions inventory</h3>
                <p>
                  EPA NEI records report facility-level annual emissions. Nearby
                  records do not show that a facility contributed to a monitor
                  reading or a place estimate.
                </p>
              </div>
            </article>
          </div>
        </section>

        <section className="about-section">
          <div className="about-section-header">
            <span className="about-kicker">Limits</span>
            <h2>What this release cannot tell you.</h2>
          </div>
          <div className="about-prose">
            <p>
              Upwind assigns estimates based on the nearest active EPA reference
              monitor, supplemented by empirical uncertainty bands derived from
              spatial cross-validation. We evaluated continuous Gaussian-kernel
              models, but retained nearest-neighbor as the transparent standard
              to avoid over-smoothing in rural areas.
            </p>
            <p>
              This atlas is designed for retrospective exploration and community
              research. It does not provide real-time air quality alerts or
              individual health exposure metrics, but rather transparent historical
              context across public environmental datasets.
            </p>
          </div>
        </section>

        <section className="about-section about-links-section">
          <div className="about-section-header">
            <span className="about-kicker">Project record</span>
            <h2>Methods, source data, and code.</h2>
          </div>
          <p className="about-prose">
            The code, national dataset build, and evaluation records are
            available in the project repository. Dataset publishers, vintages,
            selection rules, and model results are documented in the technical
            reference.
          </p>
          <div className="about-cta-buttons">
            <a className="about-btn-primary" href="/methodology">
              <FileText size={15} /> Methodology and data sources
            </a>
            <a
              className="about-btn-secondary"
              href={repository}
              target="_blank"
              rel="noopener noreferrer"
            >
              GitHub repository <ArrowUpRight size={14} />
            </a>
            <a
              className="about-btn-secondary"
              href="https://arnavpandya.com"
              target="_blank"
              rel="noopener noreferrer"
            >
              Developer portfolio <ArrowUpRight size={14} />
            </a>
            <a className="about-btn-secondary" href="/">
              <Compass size={15} /> Open the atlas
            </a>
          </div>
          <p className="about-credit">Created by Arnav Pandya.</p>
        </section>
      </article>
      <Footer />
    </main>
  );
}
