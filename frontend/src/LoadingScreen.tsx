import { Wind } from "lucide-react";
import "./loading-screen.css";

export interface LoadingScreenProps {
  message?: string;
  submessage?: string;
  fullScreen?: boolean;
}

export default function LoadingScreen({
  message = "Loading evidence…",
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
          {/* Quiet atlas-line motion; status text remains the primary signal. */}
          <svg className="breeze-lines" viewBox="0 0 220 90" fill="none">
            <path
              className="breeze-gust breeze-top"
              d="M10 24 C 65 14, 120 32, 195 20 C 205 18, 208 11, 200 7 C 192 3, 185 13, 192 22"
              stroke="#247b70"
              strokeWidth="2.2"
              strokeLinecap="round"
            />
            <path
              className="breeze-gust breeze-mid"
              d="M25 46 C 75 36, 135 54, 185 43"
              stroke="#388c81"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
            <path
              className="breeze-gust breeze-bot"
              d="M5 68 C 55 60, 105 76, 170 65 C 180 63, 183 56, 175 52 C 167 48, 161 58, 169 66"
              stroke="#247b70"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>

          {/* Static mark keeps loading calm and consistent with the atlas. */}
          <div className="bouncing-mark-wrap">
            <div className="bouncing-logo">
              <Wind size={26} strokeWidth={2.4} />
            </div>
            <div className="bouncing-shadow" />
          </div>
        </div>

        <div className="bouncing-caption">
          <div className="bouncing-title">
            <b>UPWIND</b>
            <span className="breeze-dots" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
          </div>
          <p className="bouncing-status">{message}</p>
          {submessage && <p className="loader-submessage">{submessage}</p>}
        </div>
      </div>
    </div>
  );
}
