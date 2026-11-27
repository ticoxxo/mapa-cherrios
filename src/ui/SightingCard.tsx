import { critterSVG, GROUP_INFO } from '../art/critters'
import type { SightingInfo } from '../map/MapView'
import { SIZE_LABEL, WORK_INFO, workSVG } from '../art/work'
import { pools, WATER_INFO, waterSVG } from '../art/water'
import { fmt } from '../i18n'
import { CAMPO_KIND } from '../modes'

const MONTHS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

const LICENSE: Record<string, string> = {
  cc0: 'dominio público (CC0)', 'cc-by': 'CC BY', 'cc-by-nc': 'CC BY-NC', 'cc-by-sa': 'CC BY-SA',
  'cc-by-nd': 'CC BY-ND', 'cc-by-nc-sa': 'CC BY-NC-SA', 'cc-by-nc-nd': 'CC BY-NC-ND',
}

/** Card for one iNaturalist sighting. Hover shows it; a click pins it with a link to the photo. */
export function SightingCard({ info, onClose }: { info: SightingInfo; onClose: () => void }) {
  if (info.b) return <BizCard info={info} onClose={onClose} />
  if (info.well) return <WellCard info={info} onClose={onClose} />
  if (info.field) return <FieldCard info={info} onClose={onClose} />
  const { pinned } = info
  const s = info.s!
  const g = GROUP_INFO[s.g]
  const date = s.d ? new Date(s.d + 'T12:00:00').toLocaleDateString('es-MX', { day: 'numeric', month: 'long', year: 'numeric' }) : null
  const left = Math.min(info.x + 16, window.innerWidth - 290)
  const top = Math.min(Math.max(info.y - 30, 70), window.innerHeight - 220)
  return (
    <div className={`sighting card${pinned ? ' pinned' : ''}`} style={{ left, top }} role={pinned ? 'dialog' : 'status'}>
      <div className="sighting-head">
        <span dangerouslySetInnerHTML={{ __html: critterSVG(s.g, 42) }} />
        <div>
          <div className="tt-title">{s.n}</div>
          {s.s && s.s !== s.n && <div className="tt-sub"><i>{s.s}</i></div>}
        </div>
        {pinned && <button className="close" onClick={onClose} aria-label="Cerrar">✕</button>}
      </div>
      <div className="tt-stat">
        Un {g.one} visto{date ? ` el ${date}` : ''}.{s.w ? <b> ¡Nuevo esta semana!</b> : null}
      </div>
      <div className="sighting-credit">Foto y registro: {s.u ?? 'anónimo'} en iNaturalist · {LICENSE[s.l] ?? s.l}</div>
      {pinned ? (
        <a className="sighting-link" href={`https://www.inaturalist.org/observations/${s.i}`} target="_blank" rel="noreferrer">
          Ver la foto en iNaturalist ↗
        </a>
      ) : (
        <div className="tt-hint">Haz clic para ver la foto</div>
      )}
    </div>
  )
}

/** Card for one DENUE business. No phone, e-mail or address is shown: only what it is and its size. */
function BizCard({ info, onClose }: { info: SightingInfo; onClose: () => void }) {
  const b = info.b!
  const g = WORK_INFO[b.g]
  const [y, m] = (b.a ?? '').split('-')
  const left = Math.min(info.x + 16, window.innerWidth - 290)
  const top = Math.min(Math.max(info.y - 30, 70), window.innerHeight - 200)
  return (
    <div className={`sighting card${info.pinned ? ' pinned' : ''}`} style={{ left, top }} role={info.pinned ? 'dialog' : 'status'}>
      <div className="sighting-head">
        <span dangerouslySetInnerHTML={{ __html: workSVG(b.g, 42) }} />
        <div>
          <div className="tt-title">{b.n}</div>
          <div className="tt-sub">{b.act ?? g.name}</div>
        </div>
        {info.pinned && <button className="close" onClick={onClose} aria-label="Cerrar">✕</button>}
      </div>
      <div className="tt-stat">
        {b.s >= 0 ? <>Trabajan aquí <b>{SIZE_LABEL[b.s]} personas</b>.</> : <>No se sabe cuánta gente trabaja aquí.</>}
      </div>
      {y && <div className="sighting-credit">En el directorio del INEGI desde {m ? `${MONTHS[Number(m) - 1]} de ` : ''}{y}.</div>}
    </div>
  )
}

/** Card for one REPDA well or intake. Private people are never named: their points are also rounded. */
function WellCard({ info, onClose }: { info: SightingInfo; onClose: () => void }) {
  const w = info.well!
  const u = WATER_INFO[w.u]
  const left = Math.min(info.x + 16, window.innerWidth - 290)
  const top = Math.min(Math.max(info.y - 30, 70), window.innerHeight - 230)
  const p = pools(w.v)
  return (
    <div className={`sighting card${info.pinned ? ' pinned' : ''}`} style={{ left, top }} role={info.pinned ? 'dialog' : 'status'}>
      <div className="sighting-head">
        <span dangerouslySetInnerHTML={{ __html: waterSVG(w.u, 42, true, w.k) }} />
        <div>
          <div className="tt-title">{w.k === 1 ? 'Toma de río o presa' : 'Pozo'} · {u.name.toLowerCase()}</div>
          <div className="tt-sub">{w.h || 'Particular (no mostramos nombres de personas)'}</div>
        </div>
        {info.pinned && <button className="close" onClick={onClose} aria-label="Cerrar">✕</button>}
      </div>
      <div className="tt-stat">
        Tiene permiso para sacar <b>{fmt(w.v)} m³</b> de agua al año{p >= 1 ? <> (como <b>{fmt(p)}</b> {p === 1 ? 'alberca olímpica' : 'albercas olímpicas'})</> : null}.
      </div>
      <div className="sighting-credit">
        {w.aq ? `Acuífero ${w.aq}. ` : ''}{w.d ? 'Título de un distrito de riego. ' : ''}{w.y ? `Título registrado en ${w.y}. ` : ''}
        Es lo que permite el título, no lo que se mide.{!w.h ? ' Ubicación aproximada (unos 100 m).' : ''}
      </div>
    </div>
  )
}

/** Card for one INEGI farmland polygon (Uso del Suelo y Vegetación, Serie VII). Only what INEGI says about it. */
function FieldCard({ info, onClose }: { info: SightingInfo; onClose: () => void }) {
  const f = info.field!
  const k = CAMPO_KIND[f.tipo]
  const left = Math.min(info.x + 16, window.innerWidth - 290)
  const top = Math.min(Math.max(info.y - 30, 70), window.innerHeight - 200)
  return (
    <div className={`sighting card${info.pinned ? ' pinned' : ''}`} style={{ left, top }} role={info.pinned ? 'dialog' : 'status'}>
      <div className="sighting-head">
        <span className={`field-swatch${k?.hatch ? ' hatch' : ''}`} style={{ background: k?.color }} aria-hidden="true" />
        <div>
          <div className="tt-title">{k?.label ?? f.desc}</div>
          <div className="tt-sub">{f.desc}</div>
        </div>
        {info.pinned && <button className="close" onClick={onClose} aria-label="Cerrar">✕</button>}
      </div>
      <div className="tt-stat">Esta mancha de campo mide unas <b>{fmt(f.ha)} hectáreas</b>.</div>
      <div className="sighting-credit">Carta de Uso del Suelo y Vegetación del INEGI (Serie VII, escala 1:250 000): las orillas son aproximadas.</div>
    </div>
  )
}
