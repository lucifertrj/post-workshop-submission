// mlflow.org-style backdrop:
//   1. near-black base
//   2. horizontal hue-sweep (rust → amber → forest → deep teal) concentrated
//      in the top portion, fading to black below
//   3. ~120 vertical "venetian blind" lines layered on top at low opacity
//
// Hues shift ~30deg as the user scrolls (see globals.css).
// Pure server component — no client JS.

const N_LINES = 120;

const lines = Array.from({ length: N_LINES }).map((_, i) => ({
  x: (i / N_LINES) * 100,
  // Deterministic pseudo-random opacities — no hydration drift
  o: 0.025 + ((i * 7919) % 60) / 1000,
}));

export default function BackgroundLines() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-deep">
      {/* mlflow-style: bright zone concentrated at top-center, fading to
          near-black radially. The ellipse radii (--grad-x / --grad-y) are
          animated by the scroll timeline so the gradient grows from
          ~65% → ~88% of viewport height as the user scrolls. */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage: `
            radial-gradient(
              ellipse var(--grad-x) var(--grad-y) at 50% 22%,
              transparent 0%,
              transparent 28%,
              rgba(10, 10, 12, 0.55) 68%,
              rgb(10, 10, 12) 96%
            ),
            linear-gradient(
              90deg,
              var(--grad-1) 0%,
              var(--grad-2) 33%,
              var(--grad-3) 66%,
              var(--grad-4) 100%
            )
          `,
        }}
      />
      <svg
        className="absolute inset-0 h-full w-full"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        {lines.map((l, i) => (
          <line
            key={i}
            x1={`${l.x}%`}
            y1="0"
            x2={`${l.x}%`}
            y2="100%"
            stroke="white"
            strokeOpacity={l.o}
            strokeWidth="1"
            vectorEffect="non-scaling-stroke"
          />
        ))}
      </svg>
    </div>
  );
}
