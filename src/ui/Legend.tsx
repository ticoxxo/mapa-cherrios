import { useEffect, useRef, useState } from 'react'
import { critterSVG, GROUP_INFO, GROUPS, type Group } from '../art/critters'
import { treeSVG } from '../art/trees'
import { WORK_GROUPS, WORK_INFO, workSVG, type WorkGroup } from '../art/work'
import { WATER_INFO, WATER_USES, waterSVG, type WaterUse } from '../art/water'
import type { CoreData } from '../data'
import { PLACE, fmt, t } from '../i18n'
import { DROUGHT_PLAIN, DROUGHT_RAMP, GREEN_PLAIN, GREEN_RAMP, GRS_RAMP, HEAT_RAMP, IMU_RAMP, NO_DATA, PEOPLE_RAMP, WATER_RAMP, WILD_RAMP, WORK_PLAIN, WORK_RAMP, modeState, type ModeId } from '../modes'

// Plain-language legends: written for people who have never used a map app like this.
export const WEALTH_PLAIN = ['Le falta muy poco', 'Le falta poco', 'Regular', 'Le falta mucho', 'Le falta muchísimo']

const PLANNED: Record<string, { text: string; src: string }> = {
  heat: { text: 'Qué tan caliente se pone el suelo en cada barrio en verano, visto desde satélite.', src: 'Satélites Landsat (USGS/NASA)' },
  green: { text: 'Qué tan verde está cada barrio, visto desde satélite.', src: 'Satélites Sentinel-2 (Copernicus) y ESA' },
  wildlife: { text: '', src: 'iNaturalist' },
  work: { text: 'Dónde están los negocios y las empresas grandes.', src: 'Directorio de negocios DENUE (INEGI)' },
  water: { text: 'Quién tiene permiso para sacar agua, y si hay sequía.', src: 'CONAGUA (REPDA) y Monitor de Sequía (SMN)' },
}

interface Props {
  data: CoreData
  mode: ModeId
  wealthPrimary: 'imu' | 'grs' | null
  groups: Set<Group>
  setGroups: (g: Set<Group>) => void
  workGroups: Set<WorkGroup>
  setWorkGroups: (g: Set<WorkGroup>) => void
  waterUses: Set<WaterUse>
  setWaterUses: (g: Set<WaterUse>) => void
}

export function Legend({ data, mode, wealthPrimary, groups, setGroups, workGroups, setWorkGroups, waterUses, setWaterUses }: Props) {
  const [open, setOpen] = useState(window.innerWidth > 760)
  const st = modeState(data.manifest, mode, data.era)
  const antes = data.era === 'antes'

  let body: React.ReactNode = null
  let source = ''
  if (mode === 'realm') {
    body = (
      <>
        <p>Cada color es un <b>{t('territory').toLowerCase()}</b>: un pedazo del pueblo. Acércate para ver cada barrio y, más de cerca, cada manzana.</p>
        <p className="legend-note">{t('realm_note')}</p>
      </>
    )
    source = antes ? 'INEGI, Marco Geoestadístico del Censo 2020' : 'INEGI y OpenStreetMap'
  } else if (mode === 'people') {
    const b = data.stats.breaks.dens
    const rows = PEOPLE_RAMP.map((c, i) => ({
      c,
      label: i === 0 ? `menos de ${fmt(b[0])}` : i === b.length ? `${fmt(b[b.length - 1])} o más` : `${fmt(b[i - 1])} a ${fmt(b[i])}`,
    }))
    body = (
      <>
        <p><b>¿Dónde vive más gente?</b> Entre más oscuro, más apretada vive la gente.</p>
        <Swatches rows={[...rows, { c: NO_DATA, label: t('no_data') }]} unit="personas en un cuadro de 1 km por lado" />
      </>
    )
    source = 'Censo 2020 del INEGI'
  } else if (mode === 'wealth') {
    if (st !== 'ok') {
      body = <p className="legend-unavailable"><strong>{t('unavailable')}.</strong> Esta capa aparecerá cuando consigamos los datos.</p>
      source = 'CONAPO y CONEVAL, 2020'
    } else {
      const ramp = wealthPrimary === 'imu' ? IMU_RAMP : GRS_RAMP
      body = (
        <>
          <p><b>¿Qué tanto le falta a la gente?</b> Toma en cuenta escuela, servicio médico, agua, drenaje, internet y otras cosas básicas.</p>
          <p>Azul: le falta poco. Naranja: le falta mucho.</p>
          <Swatches rows={[...ramp.map((c, i) => ({ c, label: WEALTH_PLAIN[i] })), { c: NO_DATA, label: t('no_data') }]} />
        </>
      )
      source = wealthPrimary === 'imu' ? 'CONAPO (marginación), 2020' : 'CONEVAL (rezago social), 2020'
    }
  } else if (mode === 'green' && st === 'ok' && data.stats.green) {
    const g = data.stats.green
    const n = (data.stats.breaks.ndvi ?? []).length + 1
    body = (
      <>
        <p><b>¿Qué tan verde está cada barrio?</b> Más verde, más plantas vivas. Medido desde satélite en los últimos 30 días.</p>
        <Swatches rows={[...GREEN_RAMP.slice(0, n).map((c, i) => ({ c, label: GREEN_PLAIN[i] })), { c: NO_DATA, label: t('no_data') }]} />
        <p className="legend-sub legend-tree">
          <span dangerouslySetInnerHTML={{ __html: treeSVG(26) }} />
          Los arbolitos marcan dónde el satélite ve árboles. Entre más verdes están hoy, más grande el dibujo.
        </p>
        <p className="legend-note">
          No es un conteo de árboles (aquí no hay uno público): es lo que se ve desde el espacio. Hoy se ve verde el {fmt(g.city_p_green)}% de la ciudad.
        </p>
      </>
    )
    source = 'Satélites Sentinel-2 (Copernicus) y mapa de cobertura ESA WorldCover 2021'
  } else if (mode === 'heat' && st === 'ok' && data.stats.heat) {
    const h = data.stats.heat
    const b = data.stats.breaks.lst ?? []
    const rows = HEAT_RAMP.slice(0, b.length + 1).map((c, i) => ({
      c, label: i === 0 ? `menos de ${fmt(b[0])} °C` : i === b.length ? `${fmt(b[b.length - 1])} °C o más` : `${fmt(b[i - 1])} a ${fmt(b[i])} °C`,
    }))
    body = (
      <>
        <p><b>¿Qué tan caliente se pone el suelo en verano?</b> Más oscuro, más caliente. Medido desde satélite a media mañana.</p>
        <Swatches rows={[...rows, { c: NO_DATA, label: t('no_data') }]} />
        <p className="legend-note">
          Es la temperatura del <b>suelo y los techos</b>, no del aire: por eso pasa de 50 °C. Los barrios con árboles y riego son más frescos.
          Las olitas marcan los 3 barrios más calientes.
        </p>
      </>
    )
    source = `Satélites Landsat 8 y 9 (USGS/NASA): ${h.n_scenes} días despejados de mayo a septiembre, ${h.summers[0]}–${h.summers[h.summers.length - 1]}`
  } else if (mode === 'wildlife' && st === 'ok') {
    const b = data.stats.breaks.w_n ?? []
    const counts = data.stats.wildlife?.groups ?? {}
    const toggle = (g: Group) => {
      const n = new Set(groups)
      if (n.has(g)) n.delete(g)
      else n.add(g)
      setGroups(n.size ? n : new Set(GROUPS))
    }
    const rows = [{ c: WILD_RAMP[0], label: 'ninguno' },
      ...b.map((v, i) => ({ c: WILD_RAMP[Math.min(i + 1, WILD_RAMP.length - 1)], label: i === b.length - 1 ? `${fmt(v)} o más` : v + 1 === b[i + 1] ? fmt(v) : `${fmt(v)} a ${fmt(b[i + 1] - 1)}` }))]
    body = (
      <>
        <p><b>¿Dónde ha visto animales la gente?</b> Cada dibujito es un animal que alguien fotografió. Los que brincan son de esta semana.</p>
        <div className="chips" role="group" aria-label="Qué animales mostrar">
          {GROUPS.map(g => (
            <button key={g} className={`chip${groups.has(g) ? ' on' : ''}`} aria-pressed={groups.has(g)} onClick={() => toggle(g)}>
              <span dangerouslySetInnerHTML={{ __html: critterSVG(g, 22, false) }} />
              {GROUP_INFO[g].name} <small>{fmt(counts[g] ?? 0)}</small>
            </button>
          ))}
        </div>
        <p className="legend-sub">Color del barrio: cuántos animales se han reportado ahí.</p>
        <Swatches rows={rows} />
        <p className="legend-note">Ojo: enseña dónde la gente toma fotos, no cuántos animales hay. Los animales en peligro no se ponen donde se vieron, para protegerlos.</p>
      </>
    )
    source = 'iNaturalist, solo registros confirmados por la comunidad'
  } else if (mode === 'work' && st === 'ok' && data.stats.work) {
    const w = data.stats.work
    const n = (data.stats.breaks.j_dens ?? []).length + 1
    const toggle = (g: WorkGroup) => {
      const s = new Set(workGroups)
      if (s.has(g)) s.delete(g)
      else s.add(g)
      setWorkGroups(s.size ? s : new Set(WORK_GROUPS))
    }
    body = (
      <>
        <p><b>¿Dónde está la chamba?</b> Entre más oscuro el barrio, más gente trabaja ahí (no donde vive: donde trabaja).</p>
        <Swatches rows={[...WORK_RAMP.slice(0, n).map((c, i) => ({ c, label: WORK_PLAIN[i] })), { c: NO_DATA, label: t('no_data') }]} />
        <p className="legend-sub">Acércate para ver cada negocio. Los grandes (más de 100 personas) se ven desde lejos.</p>
        <div className="chips" role="group" aria-label="Qué negocios mostrar">
          {WORK_GROUPS.map(g => (
            <button key={g} className={`chip${workGroups.has(g) ? ' on' : ''}`} aria-pressed={workGroups.has(g)} onClick={() => toggle(g)}>
              <span dangerouslySetInnerHTML={{ __html: workSVG(g, 22, false) }} />
              {WORK_INFO[g].name} <small>{fmt(w.groups[g] ?? 0)}</small>
            </button>
          ))}
        </div>
        <p className="legend-note">
          INEGI solo dice el tamaño de cada negocio en rangos (por ejemplo, «de 11 a 30 personas»). Por eso los empleos de cada barrio
          son un <b>cálculo aproximado</b>. Solo cuenta negocios con local; no cuenta a quien trabaja por su cuenta en la calle o en casa.
        </p>
      </>
    )
    source = `Directorio de negocios DENUE del INEGI, edición ${w.edition.slice(5)}/${w.edition.slice(0, 4)}`
  } else if (mode === 'water' && st === 'ok' && data.stats.water) {
    const { rights: r, drought: d } = data.stats.water
    const b = data.stats.breaks.p_tinaco ?? []
    const rows = WATER_RAMP.slice(0, b.length + 1).map((c, i) => ({
      c, label: i === 0 ? `menos del ${fmt(b[0])}%` : i === b.length ? `${fmt(b[b.length - 1])}% o más` : `${fmt(b[i - 1])} a ${fmt(b[i])}%`,
    }))
    const toggle = (u: WaterUse) => {
      const s = new Set(waterUses)
      if (s.has(u)) s.delete(u)
      else s.add(u)
      setWaterUses(s.size ? s : new Set(WATER_USES))
    }
    const date = (iso: string) => new Date(iso + 'T12:00:00').toLocaleDateString('es-MX', { day: 'numeric', month: 'long', year: 'numeric' })
    body = (
      <>
        {d && (
          <div className="drought">
            <p>
              <b>¿Hay sequía?</b>{' '}
              <span className={`pill${d.level >= 4 ? ' light' : ''}`} style={{ background: DROUGHT_RAMP[d.level] }}>{DROUGHT_PLAIN[d.level]}</span>
              {' '}desde el {date(d.since)}.
            </p>
            <svg className="drought-spark" viewBox={`0 0 ${d.series.length * 4} 22`} preserveAspectRatio="none" role="img"
              aria-label={`Sequía en ${PLACE} cada 15 días desde ${date(d.series[0][0])}`}>
              {d.series.map(([day, lv], i) => (
                <rect key={day} x={i * 4} y={22 - 4 - lv * 3.6} width={3.2} height={4 + lv * 3.6} fill={DROUGHT_RAMP[lv]}>
                  <title>{`${date(day)}: ${DROUGHT_PLAIN[lv]}`}</title>
                </rect>
              ))}
            </svg>
            <p className="legend-note">Cada rayita es un reporte (cada 15 días, desde {date(d.series[0][0])}). Más alta y más café, peor la sequía.</p>
          </div>
        )}
        <p><b>¿Quién tiene el agua?</b> Cada dibujito es un pozo (redondo) o una toma de río o presa (cuadrada) con permiso de CONAGUA. Más grande, más agua al año.</p>
        {r && (
          <div className="chips" role="group" aria-label="Qué pozos mostrar">
            {WATER_USES.map(u => (
              <button key={u} className={`chip${waterUses.has(u) ? ' on' : ''}`} aria-pressed={waterUses.has(u)} onClick={() => toggle(u)}>
                <span dangerouslySetInnerHTML={{ __html: waterSVG(u, 22, false) }} />
                {WATER_INFO[u].name} <small>{fmt(r.uses[u] ?? 0, 1)} mill. m³</small>
              </button>
            ))}
          </div>
        )}
        {b.length ? (
          <>
            <p className="legend-sub">Color del barrio: cuántas casas tienen <b>tinaco</b> (Censo 2020). Donde el agua llega a ratos, la gente la guarda.</p>
            <Swatches rows={[...rows, { c: NO_DATA, label: t('no_data') }]} />
          </>
        ) : (
          <p className="legend-sub">Los barrios van sin color: los tinacos se contaron en el Censo 2020, antes de ser municipio. Míralos en «{t('era_antes')}», modo Gente.</p>
        )}
        {r && (
          <p className="legend-note">
            En todo el municipio hay permiso para sacar <b>{fmt(r.hm3)} millones de m³</b> al año. Es lo que permiten los títulos, no lo que se mide.
            No mostramos nombres de personas: solo de empresas, ejidos y gobierno.
          </p>
        )}
      </>
    )
    source = [r && `CONAGUA, Registro Público de Derechos de Agua (corte ${r.snapshot.slice(5)}/${r.snapshot.slice(0, 4)})`,
      d && `Monitor de Sequía de México (SMN), ${date(d.date)}`, b.length > 0 && 'Censo 2020 del INEGI (tinacos)'].filter(Boolean).join(' · ')
  } else {
    const p = PLANNED[mode]
    body = <p className="legend-unavailable"><strong>{t('soon')}.</strong> {p.text}</p>
    source = p.src
  }

  // publish the legend's height so La Gaceta / Los Anales can stop above it instead of overlapping
  const ref = useRef<HTMLElement>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const root = document.documentElement.style
    const ro = new ResizeObserver(() => root.setProperty('--legend-h', `${Math.ceil(el.getBoundingClientRect().height)}px`))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  return (
    <aside ref={ref} className={`legend card${open ? '' : ' collapsed'}`} aria-label={t('legend')}>
      <button className="card-head" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span>{t(`m_${mode}`)}</span>
        <span className="chev" aria-hidden="true">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <div className="card-body">
          {body}
          <p className="legend-source">Datos: {source}</p>
        </div>
      )}
    </aside>
  )
}

function Swatches({ rows, unit }: { rows: { c: string; label: string }[]; unit?: string }) {
  return (
    <ul className="swatches">
      {rows.map(r => (
        <li key={r.label}>
          <span className="sw" style={{ background: r.c }} />
          {r.label}
        </li>
      ))}
      {unit && <li className="unit">{unit}</li>}
    </ul>
  )
}
