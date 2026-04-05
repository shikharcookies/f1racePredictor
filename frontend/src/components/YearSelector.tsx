import { useEffect, useState, useRef } from 'react';

interface Props {
  onSelect: (year: number) => void;
  selectedYear: number | null;
}

export default function YearSelector({ onSelect, selectedYear }: Props) {
  const [years, setYears] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function fetchSeasons() {
    fetch('/api/v1/seasons')
      .then(r => r.json())
      .then((data: { seasons: Record<string, unknown[]> }) => {
        const available = Object.keys(data.seasons ?? {})
          .map(Number)
          .filter(n => !isNaN(n))
          .sort((a, b) => b - a);

        if (available.length > 0) {
          setYears(available);
          setLoading(false);
          if (pollRef.current) clearInterval(pollRef.current);

          const currentYear = new Date().getFullYear();
          const defaultYear = available.includes(currentYear) ? currentYear : available[0];
          onSelect(defaultYear);
        }
      })
      .catch(() => {});
  }

  useEffect(() => {
    fetchSeasons();
    // Poll every 5 seconds until data arrives (background pipeline may still be loading)
    pollRef.current = setInterval(fetchSeasons, 5000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  if (loading) {
    return (
      <div className="year-selector">
        <label htmlFor="year-select">Season:</label>
        <select id="year-select" disabled>
          <option value="">Loading seasons...</option>
        </select>
      </div>
    );
  }

  return (
    <div className="year-selector">
      <label htmlFor="year-select">Season:</label>
      <select
        id="year-select"
        value={selectedYear ?? ''}
        onChange={e => onSelect(Number(e.target.value))}
      >
        {years.map(year => (
          <option key={year} value={year}>{year}</option>
        ))}
      </select>
    </div>
  );
}
