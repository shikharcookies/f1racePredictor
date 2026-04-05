import type { Data, Layout } from 'plotly.js';
import { useEffect, useRef } from 'react';

interface Props {
  data: Data[];
  layout?: Partial<Layout>;
  style?: React.CSSProperties;
}

export default function Plot({ data, layout = {}, style }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    let cancelled = false;

    import('plotly.js/dist/plotly.min.js').then((mod) => {
      if (cancelled || !ref.current) return;
      const Plotly = (mod as any).default ?? mod;
      Plotly.newPlot(ref.current, data, {
        ...layout,
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { color: '#e0e0e0' },
      });
    });

    return () => {
      cancelled = true;
      import('plotly.js/dist/plotly.min.js').then((mod) => {
        const Plotly = (mod as any).default ?? mod;
        if (el) Plotly.purge(el);
      });
    };
  }, [data, layout]);

  return <div ref={ref} style={style} />;
}
