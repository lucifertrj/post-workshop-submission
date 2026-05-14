"use client";
// Scroll-driven hue rotation fallback for browsers without
// `animation-timeline: scroll()` support (Firefox, Safari as of 2026).
// Chromium handles it natively via the @supports block in globals.css.
//
// We rotate the global --hue-shift custom property from 0deg to 30deg over
// the full document scroll, which slides every gradient stop in unison.

import { useEffect } from "react";

export default function ScrollHue() {
  useEffect(() => {
    if (
      typeof CSS !== "undefined" &&
      CSS.supports?.("animation-timeline: scroll()")
    ) {
      return;
    }
    const onScroll = () => {
      const max = Math.max(
        document.body.scrollHeight - window.innerHeight,
        1,
      );
      const pct = Math.min(Math.max(window.scrollY / max, 0), 1);
      const root = document.documentElement.style;
      root.setProperty("--hue-shift", `${pct * 30}deg`);
      root.setProperty("--grad-y", `${65 + pct * 23}%`);
      root.setProperty("--grad-x", `${82 + pct * 14}%`);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  return null;
}
