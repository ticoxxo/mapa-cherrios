import { useState } from 'react'
import type { CoreData } from '../data'
import { fmt, fmtDate, t } from '../i18n'

/** La Gaceta: a frontier newspaper of weekly changes. Weekly entries come from
 *  chronicle.json (written by the weekly pipeline); until it exists, the first
 *  edition prints founding notes built from real census facts. */
export function Chronicle({ data }: { data: CoreData }) {
  const [open, setOpen] = useState(window.innerWidth >= 1280)
  const s = data.stats
  const date = data.manifest.generated

  const weekly = (data.chronicle?.entries ?? []).map(e => ({ date: e.date, title: e.title ?? '', text: e.es, source: e.source }))
  const entries = [
    ...weekly,
        {
          date,
          title: 'Municipio nuevo',
          text: `En 2021 el Congreso de Sinaloa creó el municipio de ${t('title')}; antes era parte de Guasave. El mapa tiene ${fmt(s.n_ageb)} barrios de hoy. Para ver los números del Censo 2020, usa «${t('era_antes')}».`,
          source: 'INEGI, Marco Geoestadístico dic. 2025',
        },
        ...(weekly.length ? [] : [{ date, title: 'Se avisa', text: 'Cada semana aquí saldrán las noticias del pueblo: animales, verdor, calor, chamba y agua.', source: undefined }]),
      ]

  return (
    <aside className={`chronicle card${open ? '' : ' collapsed'}`} aria-label={t('chronicle')}>
      <button className="card-head" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span>{t('chronicle')}</span>
        <span className="chev" aria-hidden="true">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <ol className="card-body events">
          {entries.map((e, i) => (
            <li key={i} className="event">
              <time>{fmtDate(e.date)}</time>
              {e.title && <h4>{e.title}</h4>}
              <p>{e.text}</p>
              {e.source && <small>{e.source}</small>}
            </li>
          ))}
        </ol>
      )}
    </aside>
  )
}
