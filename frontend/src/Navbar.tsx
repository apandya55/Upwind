import { ArrowUpRight, Compass, FileText, Info, Menu, Share2, Terminal, Wind, X } from "lucide-react";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import "./navbar.css";

export interface NavbarProps {
  active?: "map" | "methodology" | "about" | "run";
  onShare?: () => void;
  shareCopied?: boolean;
  children?: ReactNode;
}

export default function Navbar({ active, onShare, shareCopied = false, children }: NavbarProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [isClosing, setIsClosing] = useState(false);

  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => {
      setMenuOpen(false);
      setIsClosing(false);
    }, 220);
  };

  const handleOpen = () => {
    setIsClosing(false);
    setMenuOpen(true);
  };

  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") handleClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  return (
    <>
      <header className="app-navbar national-header">
        <div className="app-navbar-inner">
          <a href="/" className="app-brand national-brand" aria-label="UPWIND Home">
            <span className="app-brand-mark national-brand-icon"><Wind size={16} /></span>
            <div className="app-brand-text">
              <b>UPWIND</b>
              <small>CIVIC AIR ATLAS</small>
            </div>
          </a>

          {children && <div className="app-navbar-center">{children}</div>}

          <div className="app-nav-actions national-header-actions">
            {onShare ? (
              <button
                type="button"
                onClick={onShare}
                className="app-icon-button soft-button"
                title="Share current map view"
                aria-label="Share view"
              >
                <Share2 size={13} />
                <span>{shareCopied ? "Copied" : "Share"}</span>
              </button>
            ) : (
              <a href="/" className="app-cta-button">
                Explore map <ArrowUpRight size={13} />
              </a>
            )}

            <button
              type="button"
              className="app-icon-button soft-button national-hamburger-btn"
              aria-label="Open menu"
              aria-expanded={menuOpen}
              title="Menu"
              onClick={handleOpen}
            >
              <Menu size={16} />
            </button>
          </div>
        </div>
      </header>

      {menuOpen && (
        <div className={`app-menu-overlay national-menu-overlay ${isClosing ? "is-closing" : ""}`} onClick={handleClose}>
          <aside className={`app-menu-drawer national-menu-drawer ${isClosing ? "is-closing" : ""}`} onClick={(e) => e.stopPropagation()} aria-label="Main navigation menu">
            <div className="app-menu-head national-menu-head">
              <a href="/" className="app-brand" onClick={handleClose}>
                <span className="app-brand-mark"><Wind size={15} /></span>
                <div className="app-brand-text">
                  <b>UPWIND</b>
                  <small>CIVIC AIR ATLAS</small>
                </div>
              </a>
              <button
                type="button"
                className="app-menu-close national-menu-close"
                aria-label="Close menu"
                onClick={handleClose}
              >
                <X size={15} />
              </button>
            </div>

            <nav className="app-menu-nav national-menu-nav">
              <span className="app-menu-label national-menu-section-label">DIRECTORY</span>
              <a
                href="/"
                className={`app-menu-link national-menu-item ${active === "map" ? "active" : ""}`}
                onClick={handleClose}
              >
                <div className="app-menu-icon menu-item-icon"><Compass size={16} /></div>
                <div className="app-menu-content menu-item-text">
                  <strong>National Air Atlas</strong>
                  <span>Interactive PM2.5 GIS map across 32,333 census places</span>
                </div>
              </a>

              <a
                href="/local"
                className={`app-menu-link national-menu-item ${active === "run" ? "active" : ""}`}
                onClick={handleClose}
              >
                <div className="app-menu-icon menu-item-icon"><Terminal size={16} /></div>
                <div className="app-menu-content menu-item-text">
                  <strong>Run Model Locally</strong>
                  <span>Step-by-step tutorial, GitHub repo, and model runner</span>
                </div>
              </a>

              <a
                href="/methodology"
                className={`app-menu-link national-menu-item ${active === "methodology" ? "active" : ""}`}
                onClick={handleClose}
              >
                <div className="app-menu-icon menu-item-icon"><FileText size={16} /></div>
                <div className="app-menu-content menu-item-text">
                  <strong>Scientific Methodology</strong>
                  <span>Mathematical models, spatial holdouts, and error intervals</span>
                </div>
              </a>

              <a
                href="/about"
                className={`app-menu-link national-menu-item ${active === "about" ? "active" : ""}`}
                onClick={handleClose}
              >
                <div className="app-menu-icon menu-item-icon"><Info size={16} /></div>
                <div className="app-menu-content menu-item-text">
                  <strong>About UPWIND</strong>
                  <span>Project background, data provenance, and limits</span>
                </div>
              </a>
            </nav>

            <div className="app-menu-footer national-menu-footer">
              <div className="app-menu-meta menu-footer-meta">
                <span>Release v0.3.0 · Protocol UW-NATIONAL-SPATIAL-2026-04</span>
                <span>U.S. Census Bureau · EPA AQS · EPA NEI</span>
              </div>
              <p className="app-menu-note menu-footer-disclaimer">
                Historical point estimates at Census Gazetteer centroids. Not personal exposure, forecasts, or source attribution.
              </p>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
