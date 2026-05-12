"use client";
import Link from "next/link";
import { useState } from "react";
import ImageRace from "@/components/race/ImageRace";
import SignalRace from "@/components/race/SignalRace";

type Mode = "image" | "signal";

export default function RacePage() {
  const [mode, setMode] = useState<Mode>("image");

  return (
    <main>
      <nav className="flex items-center justify-between px-8 py-6 text-sm font-mono">
        <Link
          href="/"
          className="text-cream tracking-tight hover:text-gold transition-colors"
        >
          ← proximal methods
        </Link>
        <div className="flex gap-6 text-muted">
          <Link href="/deblur" className="hover:text-gold transition-colors">
            deblur
          </Link>
          <Link href="/denoise" className="hover:text-gold transition-colors">
            recover
          </Link>
          <Link href="/race" className="text-gold">
            race
          </Link>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-8 pb-32">
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-muted mb-3">
          demo · race mode
        </p>
        <h1 className="text-4xl sm:text-5xl font-bold mb-4">
          Algorithm Race
        </h1>
        <p className="text-muted text-lg max-w-2xl mb-8 leading-relaxed">
          Pit{" "}
          <span className="text-cream">no-opt baseline</span>,{" "}
          <span className="text-cream">ISTA</span>, and{" "}
          <span className="text-gold">FISTA</span> against the same problem.
          Two SSE streams run in parallel; both convergence curves draw live.
        </p>

        {/* Sub-tabs: which problem to race */}
        <div className="inline-flex border border-line rounded-full p-1 mb-10">
          {(
            [
              { key: "image", label: "Image Deblurring" },
              { key: "signal", label: "Sparse Recovery" },
            ] as const
          ).map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setMode(t.key)}
              className={
                "px-5 py-2 rounded-full font-mono text-sm transition-colors " +
                (mode === t.key
                  ? "bg-gold text-deep"
                  : "text-muted hover:text-cream")
              }
            >
              {t.label}
            </button>
          ))}
        </div>

        {mode === "image" ? <ImageRace /> : <SignalRace />}
      </div>
    </main>
  );
}
