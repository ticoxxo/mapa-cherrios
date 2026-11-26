import { useState } from 'react'
import type { CoreData } from '../data'
import { ERAS, type Era } from '../era'
import { fmt, shortName, t } from '../i18n'

/** Época: today's municipio, or "Antes de ser Municipio" (2020, part of Guasave). Sits next to the style switch. */
export function EraToggle({ era, setEra }: { era: Era; setEra: (e: Era) => void }) {
  return (
    <div className="skin-toggle era-toggle" role="group" aria-label={t('era_label')} title={t('era_label')}>
      {ERAS.map(e => (
        <button key={e} className={`era-opt${era === e ? ' on' : ''}`} aria-pressed={era === e}
          aria-label={t(e === 'antes' ? 'era_antes' : 'era_municipio')}
          title={t(e === 'antes' ? 'era_antes_hint' : 'era_municipio_hint')} onClick={() => setEra(e)}>
          <span className="era-long">{t(e === 'antes' ? 'era_antes' : 'era_municipio')}</span>
          <span className="era-short" aria-hidden="true">{e === 'antes' ? 'Antes (2020)' : 'Hoy'}</span>
        </button>
      ))}
    </div>
  )
}

/** In the 2020 view, this card takes La Gaceta's place (La Gaceta is about this week, not 2020). */
export function EraNote({ data }: { data: CoreData }) {
  const s = data.stats
  const parent = s.parent ?? {}
  const locs = Object.entries(s.localities)
  const [open, setOpen] = useState(window.innerWidth >= 1000)
  return (
    <aside className={`chronicle card era-note${open ? '' : ' collapsed'}`} aria-label={t('era_antes')}>
      <button className="card-head" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span>{t('era_antes')}</span>
        <span className="chev" aria-hidden="true">{open ? '▾' : '▸'}</span>
      </button>
      {open && <div className="card-body">
        <p>{t('antes_note')}</p>
        <ul className="era-locs">
          {locs.map(([k, v]) => {
            const mun = data.agebs.features.find(f => (f.properties as { loc: string }).loc === k)?.properties as { mun?: string } | undefined
            return (
              <li key={k}>
                <b>{shortName(v.name) ?? k}</b>: {fmt(v.pop)} personas
                {mun?.mun && parent[mun.mun] ? <> · municipio de {parent[mun.mun]}</> : null}
              </li>
            )
          })}
        </ul>
        <p className="legend-note">En 2021 se hizo municipio y el INEGI cambió los barrios: estos números solo van en esta vista.</p>
        <small>INEGI, Censo de Población y Vivienda 2020 y Marco Geoestadístico 2020</small>
      </div>}
    </aside>
  )
}
