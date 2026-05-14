"use client";

export default function ImageCanvas({
  src,
  title,
  caption,
}: {
  src: string | null;
  title: string;
  caption?: string;
}) {
  return (
    <div className="flex flex-col">
      <div className="font-mono text-xs uppercase tracking-wider text-muted mb-2">
        {title}
      </div>
      <div className="relative aspect-square border border-line rounded-lg overflow-hidden bg-deep/60 flex items-center justify-center">
        {src ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={src}
            alt={title}
            className="block w-full h-full object-cover"
            style={{ imageRendering: "auto" }}
          />
        ) : (
          <div className="text-muted/50 font-mono text-xs">no data</div>
        )}
      </div>
      {caption && (
        <div className="mt-2 font-mono text-xs text-cream/70 tabular">
          {caption}
        </div>
      )}
    </div>
  );
}
