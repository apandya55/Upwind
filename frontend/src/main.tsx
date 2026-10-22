import React from "react";
import ReactDOM from "react-dom/client";
import { lazy, Suspense } from "react";
import LoadingScreen from "./LoadingScreen";
const App = lazy(() => import("./App"));
const Landing = lazy(() => import("./Landing"));
const LocalPage = lazy(() => import("./LocalPage"));
const NationalExplorer = lazy(() => import("./national/NationalExplorer"));
import "./style.css";
import "./atlas-system.css";
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Suspense
      fallback={
        <LoadingScreen
          fullScreen={true}
          message="Loading UPWIND…"
          submessage="Preparing public atmospheric atlas and national geospatial layers"
        />
      }
    >
      {location.pathname === "/workspace" ? <App /> : location.pathname === "/local" ? <LocalPage /> : location.pathname === "/explore" || location.pathname === "/national" ? <NationalExplorer /> : <Landing />}
    </Suspense>
  </React.StrictMode>,
);
