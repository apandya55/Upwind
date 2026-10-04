import {
  Compass,
  FileText,
  Info,
  Menu,
  Share2,
  Terminal,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import BrandMark from "./BrandMark";
import "./navbar.css";

export interface NavbarProps {
  active?: "map" | "methodology" | "about" | "run";
  onShare?: () => void;
  shareCopied?: boolean;
  children?: ReactNode;
}

export default function Navbar({
  active,
  onShare,
  shareCopied = false,
  children,
}: NavbarProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const closeTimer = useRef<number | null>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  const handleClose = () => {
    if (!menuOpen) return;
    setIsClosing(true);
    if (closeTimer.current !== null) window.clearTimeout(closeTimer.current);
    closeTimer.current = window.setTimeout(() => {
      setMenuOpen(false);
      setIsClosing(false);
      closeTimer.current = null;
      menuButtonRef.current?.focus();
    }, 220);
  };

  const handleOpen = () => {
    if (closeTimer.current !== null) {
      window.clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
    setIsClosing(false);
    setMenuOpen(true);
  };

  useEffect(() => {
    if (!menuOpen) {
      document.body.style.removeProperty("overflow");
      return;
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") handleClose();
    };
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.removeProperty("overflow");
    };
  }, [menuOpen]);

  useEffect(
    () => () => {
      if (closeTimer.current !== null) window.clearTimeout(closeTimer.current);
      document.body.style.removeProperty("overflow");
    },
    [],
  );

  return (
    <>
      <header
        className={`app-navbar national-header ${children ? "has-toolbar" : "drawer-only"}`}
      >
        <div className="app-navbar-inner">
          <a
            href="/"
            className="app-brand national-brand"
            aria-label="UPWIND Home"
          >
            <span className="app-brand-mark national-brand-icon">
              <BrandMark />
            </span>
            <div className="app-brand-text">
              <b>UPWIND</b>
              <small>Public air atlas</small>
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
            ) : null}

            <button
              type="button"
              className="app-icon-button soft-button national-hamburger-btn"
              aria-label="Open menu"
              aria-controls="upwind-navigation-drawer"
              aria-expanded={menuOpen}
              title="Menu"
              ref={menuButtonRef}
              onClick={handleOpen}
            >
              <Menu size={16} />
            </button>
          </div>
        </div>
      </header>

      {menuOpen && (
        <div
          className={`app-menu-overlay national-menu-overlay ${isClosing ? "is-closing" : ""}`}
          onClick={handleClose}
        >
          <aside
            id="upwind-navigation-drawer"
            className={`app-menu-drawer national-menu-drawer ${isClosing ? "is-closing" : ""}`}
            onClick={(e) => e.stopPropagation()}
            aria-label="Main navigation menu"
            role="dialog"
            aria-modal="true"
          >
            <div className="app-menu-head national-menu-head">
              <a href="/" className="app-brand" onClick={handleClose}>
                <span className="app-brand-mark">
                  <BrandMark />
                </span>
                <div className="app-brand-text">
                  <b>UPWIND</b>
                  <small>Public air atlas</small>
                </div>
              </a>
              <button
                type="button"
                className="app-menu-close national-menu-close"
                aria-label="Close menu"
                ref={closeButtonRef}
                onClick={handleClose}
              >
                <X size={15} />
              </button>
            </div>

            <nav className="app-menu-nav national-menu-nav">
              <span className="app-menu-label national-menu-section-label">
                Explore
              </span>
              <a
                href="/explore"
                className={`app-menu-link national-menu-item ${active === "map" ? "active" : ""}`}
                onClick={handleClose}
              >
                <div className="app-menu-icon menu-item-icon">
                  <Compass size={16} />
                </div>
                <div className="app-menu-content menu-item-text">
                  <strong>National air atlas</strong>
                  <span>Browse PM2.5 records across 32,333 Census places</span>
                </div>
              </a>

              <a
                href="/local"
                className={`app-menu-link national-menu-item ${active === "run" ? "active" : ""}`}
                onClick={handleClose}
              >
                <div className="app-menu-icon menu-item-icon">
                  <Terminal size={16} />
                </div>
                <div className="app-menu-content menu-item-text">
                  <strong>Run Model Locally</strong>
                  <span>
                    Setup instructions, source code, and the local workspace
                  </span>
                </div>
              </a>

              <a
                href="/methodology"
                className={`app-menu-link national-menu-item ${active === "methodology" ? "active" : ""}`}
                onClick={handleClose}
              >
                <div className="app-menu-icon menu-item-icon">
                  <FileText size={16} />
                </div>
                <div className="app-menu-content menu-item-text">
                  <strong>Methodology</strong>
                  <span>
                    Model details, spatial tests, and uncertainty intervals
                  </span>
                </div>
              </a>

              <a
                href="/about"
                className={`app-menu-link national-menu-item ${active === "about" ? "active" : ""}`}
                onClick={handleClose}
              >
                <div className="app-menu-icon menu-item-icon">
                  <Info size={16} />
                </div>
                <div className="app-menu-content menu-item-text">
                  <strong>About UPWIND</strong>
                  <span>What the atlas contains and what it can show</span>
                </div>
              </a>
            </nav>

            <div className="app-menu-footer national-menu-footer">
              <div className="app-menu-meta menu-footer-meta">
                <span>Release v0.3.0 · 2024–2025 Data</span>
                <span>U.S. Census Bureau · EPA AQS · EPA NEI</span>
              </div>
              <p className="app-menu-note menu-footer-disclaimer">
                Historical estimates based on federal reference monitoring and Census data.
              </p>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
