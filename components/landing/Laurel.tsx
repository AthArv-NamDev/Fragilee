// A laurel wreath that wraps a big number: a curved stem with leaves along it. Original drawing.
const pt = (t: number) => { // point and direction on the stem, a cubic curve from the bottom to the top
  const P = [[28, 92], [2, 68], [2, 28], [26, 6]]; const u = 1 - t;
  const x = u ** 3 * P[0][0] + 3 * u * u * t * P[1][0] + 3 * u * t * t * P[2][0] + t ** 3 * P[3][0];
  const y = u ** 3 * P[0][1] + 3 * u * u * t * P[1][1] + 3 * u * t * t * P[2][1] + t ** 3 * P[3][1];
  const dx = 3 * u * u * (P[1][0] - P[0][0]) + 6 * u * t * (P[2][0] - P[1][0]) + 3 * t * t * (P[3][0] - P[2][0]);
  const dy = 3 * u * u * (P[1][1] - P[0][1]) + 6 * u * t * (P[2][1] - P[1][1]) + 3 * t * t * (P[3][1] - P[2][1]);
  return { x, y, a: (Math.atan2(dy, dx) * 180) / Math.PI };
};
const LEAVES = [0.1, 0.24, 0.38, 0.52, 0.66, 0.8].flatMap((t) => { const p = pt(t); return [{ ...p, side: 1 }, { ...p, side: -1 }]; });

function Branch({ flip }: { flip?: boolean }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 44 98" className="h-16 md:h-24 fill-coral" style={{ transform: flip ? "scaleX(-1)" : undefined }}>
      <path d="M28 92 C 2 68, 2 28, 26 6" fill="none" stroke="var(--color-high)" strokeWidth="2.5" strokeLinecap="round" />
      {LEAVES.map((l, i) => <ellipse key={i} cx={l.x + l.side * 5 * Math.cos(((l.a + 90) * Math.PI) / 180)} cy={l.y + l.side * 5 * Math.sin(((l.a + 90) * Math.PI) / 180)} rx="3.2" ry="8" transform={`rotate(${l.a + 90 + l.side * 38} ${l.x + l.side * 5 * Math.cos(((l.a + 90) * Math.PI) / 180)} ${l.y + l.side * 5 * Math.sin(((l.a + 90) * Math.PI) / 180)})`} />)}
    </svg>
  );
}

export default function Laurel({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-center gap-1 md:gap-3">
      <Branch />
      <div className="text-center">{children}</div>
      <Branch flip />
    </div>
  );
}
