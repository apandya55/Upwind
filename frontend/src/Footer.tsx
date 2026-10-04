import { ArrowUpRight } from "lucide-react";
import "./footer.css";
import BrandMark from "./BrandMark";

const outbound = { target: "_blank", rel: "noopener noreferrer" } as const;

export default function Footer() {
  return (
    <footer className="app-footer">
      <div className="app-footer-inner">
        <div className="app-footer-grid">
          <div className="app-footer-brand">
            <div className="footer-brand-lockup">
              <BrandMark />
              <b>UPWIND</b>
            </div>
            <span className="footer-brand-subtitle">Public air atlas</span>
            <p>
              An independent project for exploring historical air-quality
              evidence and its limits.
            </p>
          </div>
          <div className="app-footer-col">
            <h4>Project</h4>
            <ul>
              <li>
                <a href="/">National Explorer</a>
              </li>
              <li>
                <a href="/methodology">Methodology</a>
              </li>
              <li>
                <a href="/about">About</a>
              </li>
            </ul>
          </div>
          <div className="app-footer-col">
            <h4>Data sources</h4>
            <ul>
              <li>
                <a
                  href="https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html"
                  {...outbound}
                >
                  Census Gazetteer <ArrowUpRight size={11} />
                </a>
              </li>
              <li>
                <a href="https://www.epa.gov/aqs" {...outbound}>
                  EPA Air Quality System <ArrowUpRight size={11} />
                </a>
              </li>
              <li>
                <a
                  href="https://www.epa.gov/air-emissions-inventories/2023-national-emissions-inventory-nei-data"
                  {...outbound}
                >
                  EPA 2023 NEI <ArrowUpRight size={11} />
                </a>
              </li>
            </ul>
          </div>
          <div className="app-footer-col">
            <h4>More</h4>
            <ul>
              <li>
                <a href="https://github.com/apandya55/Upwind" {...outbound}>
                  GitHub <ArrowUpRight size={11} />
                </a>
              </li>
              <li>
                <a href="https://arnavpandya.com" {...outbound}>
                  Developer portfolio <ArrowUpRight size={11} />
                </a>
              </li>
            </ul>
          </div>
        </div>
        <div className="app-footer-bottom">
          <span>
            Created by Arnav Pandya · © {new Date().getFullYear()} UPWIND
          </span>
          <span>
            Historical air quality data based on official EPA and Census records.
          </span>
        </div>
      </div>
    </footer>
  );
}
