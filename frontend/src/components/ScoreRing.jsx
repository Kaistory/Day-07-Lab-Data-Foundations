import '../styles/scoreRing.css';

/**
 * Hiển thị score (0..1) dạng vòng tròn phần trăm.
 * Màu theo mức: xanh (>=70%), cam (40-69%), đỏ (<40%).
 */
export function ScoreRing({ score = 0, size = 46 }) {
  const pct = Math.round(Math.max(0, Math.min(1, score)) * 100);
  const stroke = 4;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - pct / 100);
  const color = pct >= 70 ? '#16a34a' : pct >= 40 ? '#f59e0b' : '#dc2626';

  return (
    <div className="score-ring" style={{ width: size, height: size }} title={`Độ tin cậy ${pct}%`}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="#e5e7eb" strokeWidth={stroke}
        />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke={color} strokeWidth={stroke}
          strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: 'stroke-dashoffset 0.6s ease' }}
        />
        <text
          x="50%" y="50%" textAnchor="middle" dominantBaseline="central"
          className="score-ring-text" fill={color}
        >
          {pct}%
        </text>
      </svg>
    </div>
  );
}
