import type { Band } from "@/lib/types";
import { BAND_STYLE } from "@/lib/format";

// A quarter, half, three quarters or a full ring for Low to Critical, plus a glyph and the word, so colour is never the only cue.
export default function BandRing({ band, size = 168 }: { band: Band; size?: number }) {
  const s = BAND_STYLE[band];
  const stroke = 12;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div className="relative inline-block" style={{ width: size, height: size }} role="img" aria-label={`Risk band: ${band}`}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(220,225,232,.1)" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={s.color} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={`${c * s.fill} ${c}`} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-2xl ${s.text}`} aria-hidden="true">{s.glyph}</span>
        <span className="font-display text-xl">{band}</span>
      </div>
    </div>
  );
}
