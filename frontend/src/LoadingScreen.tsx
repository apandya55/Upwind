import "./loading-screen.css";

export interface LoadingScreenProps {
  message?: string;
  submessage?: string;
  fullScreen?: boolean;
}

export default function LoadingScreen({
  message = "Loading UPWIND…",
  submessage,
  fullScreen = true,
}: LoadingScreenProps) {
  return (
    <div
      className={`national-loading-screen ${fullScreen ? "is-fullscreen" : "is-panel"}`}
      id="upwind-loading-screen"
      role="status"
      aria-live="polite"
      aria-label="Loading UPWIND"
    >
      <span className="sr-only">
        {submessage ? `${message} — ${submessage}` : message}
      </span>
      <div className="national-loading-tile" aria-hidden="true">
        <svg
          className="national-loading-svg"
          viewBox="0 0 51 48"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <linearGradient id="streamGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="0.28" />
              <stop offset="100%" stopColor="#ffffff" stopOpacity="1" />
            </linearGradient>
          </defs>
          <g className="track" strokeWidth="4">
            <path d="M 3,13 h 31 c 8,0 11,-8 5,-11" />
            <path d="M 3,24 h 45" />
            <path d="M 3,35 h 25 c 8,0 11,8 5,11" />
          </g>
          <g stroke="url(#streamGrad)" strokeWidth="4">
            <path
              className="wind-stream stream-top"
              d="M 3,13 h 31 c 8,0 11,-8 5,-11"
            />
            <path className="wind-stream stream-mid" d="M 3,24 h 45" />
            <path
              className="wind-stream stream-bot"
              d="M 3,35 h 25 c 8,0 11,8 5,11"
            />
          </g>
        </svg>
      </div>
    </div>
  );
}
