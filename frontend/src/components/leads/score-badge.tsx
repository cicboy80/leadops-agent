import clsx from 'clsx';

interface ScoreBadgeProps {
  score: number;
  tier?: 'HOT' | 'WARM' | 'COLD' | null;
  showScore?: boolean;
}

export function ScoreBadge({ score, tier, showScore = true }: ScoreBadgeProps) {
  const displayTier = tier || (score >= 70 ? 'HOT' : score >= 40 ? 'WARM' : 'COLD');

  const tierStyles = {
    HOT: 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800',
    WARM: 'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800',
    COLD: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-800',
  };

  return (
    <div className={clsx(
      'inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold border',
      tierStyles[displayTier]
    )}>
      <span>{displayTier}</span>
      {showScore && <span className="opacity-75">{score}</span>}
    </div>
  );
}
