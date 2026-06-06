"use client";

/**
 * Test page — renders all four Energica model configurators.
 * Used for visual inspection and layer-toggle QA.
 */

import React, { useState } from "react";
import EnergiccaConfigurator from "../components/EnergiccaConfigurator";

type Model = "eva_ribelle" | "essesse9" | "ego" | "experia";

const MODELS: Model[] = ["eva_ribelle", "essesse9", "ego", "experia"];

const MODEL_LABELS: Record<Model, string> = {
  eva_ribelle: "EVA RIBELLE",
  essesse9: "ESSESSE9",
  ego: "EGO",
  experia: "EXPERIA",
};

const tabBarStyle: React.CSSProperties = {
  display: "flex",
  gap: "0",
  borderBottom: "1px solid var(--border-color, #eee)",
  backgroundColor: "var(--bg-primary, #fff)",
  padding: "0 40px",
};

const tabStyle = (active: boolean): React.CSSProperties => ({
  fontFamily: "var(--font-primary, 'Barlow Condensed', sans-serif)",
  fontWeight: 700,
  fontSize: "13px",
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  padding: "16px 20px",
  cursor: "pointer",
  border: "none",
  borderBottom: active ? "2px solid var(--accent, #78BE20)" : "2px solid transparent",
  backgroundColor: "transparent",
  color: active ? "var(--text-primary, #121212)" : "var(--text-secondary, #757575)",
  transition: "color 150ms ease, border-color 150ms ease",
  marginBottom: "-1px",
});

export default function TestPage() {
  const [activeModel, setActiveModel] = useState<Model>("eva_ribelle");
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  const switchModel = (m: Model) => {
    // Clear URL params so each model starts from its own defaults
    if (typeof window !== "undefined") {
      window.history.replaceState(null, "", window.location.pathname);
    }
    setActiveModel(m);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "var(--bg-primary, #fff)",
        color: "var(--text-primary, #121212)",
      }}
    >
      {/* Model selector tabs */}
      <nav style={tabBarStyle} aria-label="Model selector">
        {MODELS.map((m) => (
          <button
            key={m}
            type="button"
            style={tabStyle(m === activeModel)}
            onClick={() => switchModel(m)}
            aria-selected={m === activeModel}
            role="tab"
          >
            {MODEL_LABELS[m]}
          </button>
        ))}
      </nav>

      {/* Active configurator */}
      <EnergiccaConfigurator
        key={activeModel}
        model={activeModel}
        apiUrl={apiUrl}
      />
    </div>
  );
}
