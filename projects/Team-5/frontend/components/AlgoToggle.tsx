"use client";
import type { Algo } from "@/lib/types";

export default function AlgoToggle({
  value,
  onChange,
  disabled,
}: {
  value: Algo;
  onChange: (a: Algo) => void;
  disabled?: boolean;
}) {
  return (
    <label className="block">
      <div className="font-mono text-xs uppercase tracking-wider text-muted mb-1.5">
        algorithm
      </div>
      <div className="inline-flex rounded-full border border-line p-1">
        {(["ista", "fista"] as Algo[]).map((a) => (
          <button
            key={a}
            type="button"
            disabled={disabled}
            onClick={() => onChange(a)}
            className={
              "px-4 py-1.5 rounded-full font-mono text-sm transition-colors " +
              (value === a
                ? "bg-gold text-deep"
                : "text-muted hover:text-cream")
            }
          >
            {a.toUpperCase()}
          </button>
        ))}
      </div>
    </label>
  );
}
