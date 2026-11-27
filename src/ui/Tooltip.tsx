import { crestSVG } from '../art/heraldry'
import { realmLabel } from '../atlasNames'
import { fmt, t } from '../i18n'
import type { Skin } from '../skin'
import type { HoverInfo, Tier } from '../map/MapView'
import type { ModeId } from '../modes'
import { WEALTH_PLAIN } from './Legend'

export function Tooltip({ h, mode, tier, skin, era }: { h: HoverInfo; mode: ModeId; tier: Tier; skin: Skin; era: 'municipio' | 'antes' }) {
  const { ageb: a, realm: r } = h
  const zoneView = tier === 'realm'
  const atlas = skin === 'atlas'
  const L = realmLabel(r, skin)
  const zone = L.zone

  let stat: React.ReactNode
  if (zoneView) {
    stat = <>Aquí viven <b>{fmt(r.pop)}</b> personas, en {r.n_ageb} barrios.</>
  } else if (mode === 'wealth') {
    const g = a.imu_grade ?? a.grs_grade
    stat = g ? <><b>{WEALTH_PLAIN[g - 1]}</b> (escuela, salud, servicios)</> : <>{t('no_data')}</>
  } else if (mode === 'work') {
    stat = a.j_n != null ? (a.j_n ? <><b>{fmt(a.j_n)}</b> {a.j_n === 1 ? 'negocio' : 'negocios'}, cerca de <b>{fmt(a.j_emp)}</b> empleos</> : <>Aquí no hay negocios registrados</>) : <>{t('no_data')}</>
  } else if (mode === 'water') {
    stat = a.p_tinaco != null
      ? <><b>{fmt(a.p_tinaco)}%</b> de las casas tienen tinaco{a.a_n ? <>; aquí hay <b>{fmt(a.a_n)}</b> {a.a_n === 1 ? 'pozo' : 'pozos'} con permiso</> : null}</>
      : <>{t('no_data')}</>
  } else if (mode === 'green') {
    stat = a.p_green != null ? <>Hoy se ve verde el <b>{fmt(a.p_green)}%</b> del barrio</> : <>{t('no_data')}</>
  } else if (mode === 'campo') {
    stat = a.c_crop != null ? <>Se ve sembrado el <b>{fmt(a.c_crop)}%</b> del barrio (visto desde satélite)</> : <>{t('no_data')}</>
  } else if (mode === 'heat') {
    stat = a.lst != null ? <>En verano el suelo llega a <b>{fmt(a.lst)} °C</b></> : <>{t('no_data')}</>
  } else if (mode === 'wildlife') {
    stat = a.w_n ? <><b>{fmt(a.w_n)}</b> {a.w_n === 1 ? 'animal reportado' : 'animales reportados'} aquí</> : <>Nadie ha reportado animales aquí todavía.</>
  } else if (!a.in_census) {
    stat = <i>{era === 'antes' ? t('no_census') : 'Sin datos del censo en los barrios de hoy'}</i>
  } else {
    stat = <>Aquí viven <b>{fmt(a.pop)}</b> personas.</>
  }

  const left = Math.min(h.x + 18, window.innerWidth - 280)
  const top = Math.max(h.y - 20, 70)
  return (
    <div className="tooltip card" style={{ left, top }} role="status">
      <div className="tt-head">
        <span dangerouslySetInnerHTML={{ __html: crestSVG(skin, r.color, r.charge, 26) }} />
        <div>
          <div className="tt-title">{zoneView ? (atlas ? <span className="rune">{L.name}</span> : zone) : `Barrio en ${zone}`}</div>
          <div className="tt-sub">{zoneView ? L.sub : `n.º ${a.ageb}`}</div>
        </div>
      </div>
      <div className="tt-stat">{stat}</div>
      <div className="tt-hint">{zoneView ? 'Haz clic para acercarte' : t('click_hint')}</div>
    </div>
  )
}
