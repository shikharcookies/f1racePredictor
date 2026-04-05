import { useEffect, useState } from 'react';
import type { GrandPrixItem, SeasonEvent } from '../types';

interface Props {
  onSelect: (slug: string, seasonEvent?: SeasonEvent) => void;
  selectedSlug: string | null;
  year?: number | null;
}

export default function GrandPrixSelector({ onSelect, selectedSlug, year }: Props) {
  const [items, setItems] = useState<GrandPrixItem[]>([]);
  const [seasonEvents, setSeasonEvents] = useState<SeasonEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    if (year != null) {
      fetch(`/api/v1/seasons/${year}/grand-prix`)
        .then(r => r.json())
        .then((data: SeasonEvent[]) => {
          setSeasonEvents(data);
          setItems([]);
          if (data.length > 0) {
            onSelect(data[data.length - 1].gp_slug, data[data.length - 1]);
          }
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    } else {
      fetch('/api/v1/grand-prix')
        .then(r => r.json())
        .then((data: GrandPrixItem[]) => {
          setItems(data);
          setSeasonEvents([]);
          if (data.length > 0) {
            onSelect(data[data.length - 1].slug);
          }
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [year]);

  const options = year != null
    ? seasonEvents.map(e => ({ value: e.gp_slug, label: e.display_name, event: e }))
    : items.map(i => ({ value: i.slug, label: i.display_name, event: undefined }));

  return (
    <div className="gp-selector">
      <label htmlFor="gp-select">Grand Prix:</label>
      <select
        id="gp-select"
        disabled={loading}
        value={selectedSlug ?? ''}
        onChange={e => {
          const opt = options.find(o => o.value === e.target.value);
          onSelect(e.target.value, opt?.event);
        }}
      >
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  );
}
