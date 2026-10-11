export default function ScoreBadge({ score, label = "Match Score" }) {
  const numericScore = Math.max(0, Math.min(100, Number(score) || 0));
  const circumference = 251.2;
  return (
    <div className="score-badge" aria-label={`${label}: ${numericScore}%`}>
      <span className="score-badge-label">{label}</span>
      <div className="radial-progress" role="img" aria-label={`${numericScore}%`}>
        <svg aria-hidden="true">
          <circle className="circle-bg" cx="45" cy="45" r="36" />
          <circle className="circle-val" cx="45" cy="45" r="36" style={{ strokeDashoffset: circumference - (circumference * numericScore) / 100 }} />
        </svg>
        <span className="radial-progress-value">{numericScore}%</span>
      </div>
    </div>
  );
}
