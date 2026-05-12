"use client";

type Props = {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  format?: (v: number) => string;
  onChange: (v: number) => void;
  disabled?: boolean;
};

export default function ParamSlider({
  label,
  value,
  min,
  max,
  step,
  format,
  onChange,
  disabled,
}: Props) {
  const display = format ? format(value) : value.toString();
  return (
    <label className="block">
      <div className="flex items-baseline justify-between mb-1.5">
        <span className="font-mono text-xs uppercase tracking-wider text-muted">
          {label}
        </span>
        <span className="font-mono text-sm tabular text-cream">{display}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
    </label>
  );
}
