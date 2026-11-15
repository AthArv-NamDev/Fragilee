// A hand-torn looking edge between two sections. Fill it with the colour of the section it belongs to.
export default function Wave({ color, flip = false, className = "" }: { color: string; flip?: boolean; className?: string }) {
  const d = `M0 12 q10 -9 20 0${" t20 0".repeat(71)} V24 H0 Z`;
  return (
    <svg aria-hidden="true" viewBox="0 0 1440 24" preserveAspectRatio="none" className={`block w-full h-4 md:h-6 ${className}`} style={{ transform: flip ? "scaleY(-1)" : undefined }}>
      <path d={d} fill={color} />
    </svg>
  );
}
