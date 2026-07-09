"use client";

interface ScoreGaugeProps {
  score: number;
  grade: string;
  animated?: boolean;
}

export function ScoreGauge({ score, grade, animated = true }: ScoreGaugeProps) {
  const circumference = 2 * Math.PI * 45;
  const offset = circumference - (score / 100) * circumference;

  const gradeColor =
    score >= 90 ? "text-green-500" :
    score >= 80 ? "text-blue-500" :
    score >= 70 ? "text-yellow-500" :
    score >= 60 ? "text-orange-500" : "text-red-500";

  return (
    <div className="relative flex flex-col items-center">
      <svg width="200" height="200" viewBox="0 0 100 100" className="-rotate-90">
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke="currentColor"
          strokeWidth="6"
          className="text-muted"
        />
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke="currentColor"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={animated ? circumference : offset}
          className={cn(`${gradeColor} ${animated ? "animate-gauge-fill" : ""}`)}
          style={animated ? ({ "--gauge-offset": offset } as React.CSSProperties) : undefined}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono text-4xl font-bold">{score}</span>
        <span className={`font-mono text-2xl font-semibold ${gradeColor}`}>{grade}</span>
      </div>
    </div>
  );
}

function cn(...classes: (string | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}
