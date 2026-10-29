import { Wind } from "lucide-react";
import "./loading-screen.css";

export interface LoadingScreenProps {
  message?: string;
  submessage?: string;
  fullScreen?: boolean;
}

export default function LoadingScreen({
  message = "Loading map data…",
  submessage,
  fullScreen = false,
}: LoadingScreenProps) {
  return (
    <div
      className={`national-loading-screen ${fullScreen ? "is-fullscreen" : "is-panel"}`}
      role="status"
      aria-live="polite"
      aria-label="Loading UPWIND"
    >
      <div className="bouncing-loader">
        <div className="breeze-stage" aria-hidden="true">
          {/* Keep the loading cue small and legible while the map data arrives. */}
          <svg className="breeze-lines" viewBox="0 0 120 40" fill="none">
            <path
              className="breeze-gust breeze-top"
              d="M18 20 C 42 20, 78 20, 102 20"
              stroke="#1b4332"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>

          <div className="bouncing-mark-wrap">
            <div className="bouncing-logo">
              <Wind size={22} strokeWidth={2} />
            </div>
          </div>
        </div>

        <div className="bouncing-caption">
          <div className="bouncing-title">
            <b>UPWIND</b>
          </div>
          <p className="bouncing-status">{message}</p>
          {submessage && <p className="loader-submessage">{submessage}</p>}
        </div>
      </div>
    </div>
  );
}
