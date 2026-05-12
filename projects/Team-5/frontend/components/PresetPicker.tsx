"use client";

type Option = { value: string; label: string };

export default function PresetPicker({
  label,
  options,
  value,
  onChange,
  disabled,
}: {
  label: string;
  options: Option[];
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <label className="block">
      <div className="font-mono text-xs uppercase tracking-wider text-muted mb-1.5">
        {label}
      </div>
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-deep/60 border border-line text-cream rounded-md px-3 py-2 font-mono text-sm focus:outline-none focus:border-gold/60"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
