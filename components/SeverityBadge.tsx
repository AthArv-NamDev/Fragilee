type Severity = 'low' | 'medium' | 'high' | 'critical';

const styles: Record<Severity, string> = {
  low: 'bg-low/15 text-low',
  medium: 'bg-medium/15 text-medium',
  high: 'bg-high/15 text-high',
  critical: 'bg-critical/15 text-critical',
};

const icons: Record<Severity, string> = { low: '●', medium: '▲', high: '◆', critical: '✦' };

export default function SeverityBadge({ level }: { level: Severity }) {
  return (
    <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${styles[level]}`}>
      {icons[level]} {level.charAt(0).toUpperCase() + level.slice(1)}
    </span>
  );
}