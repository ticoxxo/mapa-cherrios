import { crestSVG } from '../art/heraldry'
import { atlasGloss, realmLabel } from '../atlasNames'
import type { Skin } from '../skin'
import { Portrait } from '../art/Portrait'
import type { Ageb, CoreData, Realm } from '../data'
import { describe } from '../describe'
import { fmt, t, PLACE } from '../i18n'
import { GRS_RAMP, IMU_RAMP } from '../modes'
import { critterSVG, GROUP_INFO, GROUPS } from '../art/critters'
import { WEALTH_PLAIN } from './Legend'
import { GREEN_PLAIN, greenClass, WORK_PLAIN, workClass } from '../modes'
import { WORK_GROUPS, WORK_INFO, workSVG } from '../art/work'
import { pools } from '../art/water'

/** `typ` = the median barrio of the town (Sencillo skin only); drawn as a tick on the bar. */
function Bar({ label, value, color = '#8c5a3c', typ }: { label: string; value: number | null; color?: string; typ?: number }) {
  return (
    <div className="bar" title={typ != null ? `Barrio típico de ${PLACE}: ${fmt(typ)}%` : undefined}>
      <span className="bar-label">{label}</span>
      <span className="bar-track">
        <span className="bar-fill" style={{ width: `${value ?? 0}%`, background: color }} />
        {typ != null && <span className="bar-mark" style={{ left: `${typ}%` }} aria-hidden="true" />}
      </span>
      <span className="bar-val">{value == null ? '—' : `${fmt(value)}%`}</span>
    </div>
  )
}

function Stat({ label, value, typ }: { label: string; value: string; typ?: string }) {
  return (
    <div className="stat">
      <span className="stat-val">{value}</span>
      <span className="stat-label">{label}</span>
      {typ != null && <span className="stat-cmp">típico: {typ}</span>}
    </div>
  )
}

/** Ficha del barrio: a wanted-poster-style sheet for one AGEB. */
export function ProvincePanel({ data, ageb: a, realm: r, skin, onClose }: { data: CoreData; ageb: Ageb; realm: Realm; skin: Skin; onClose: () => void }) {
  const b = data.stats.breaks.dens
  const rank = a.dens == null ? null : Math.min(1, b.filter(x => a.dens! >= x).length / b.length)
  const pct = (x: number | null, of: number | null) => (x != null && of ? (100 * x) / of : null)
  const src = data.manifest.sources
  const atlas = skin === 'atlas'
  const plain = skin === 'sencillo'
  const L = realmLabel(r, skin)
  // Sencillo compares with the median barrio (already in stats.json); never shown when missing
  const typ = (k: string): number | undefined => (plain ? data.stats.ranges[k]?.[2] : undefined)
  const typS = (k: string, digits = 0) => {
    const v = typ(k)
    return v == null ? undefined : fmt(v, digits)
  }
  const zone = L.zone
  const lsts = data.agebs.features.map(f => (f.properties as Ageb).lst).filter((x): x is number => x != null)
  const heatRank = a.lst == null || !lsts.length ? null : Math.round((100 * lsts.filter(x => x < a.lst!).length) / lsts.length)
  const top = (a.w_top ?? '').split('|').filter(Boolean).map(x => x.split(':'))

  return (
    <aside className="panel card" aria-label={`Barrio en ${zone}`}>
      <div className="sheet-grip" aria-hidden="true" />
      <header className="panel-head" style={{ ['--realm' as string]: r.color }}>
        <span className="panel-shield" dangerouslySetInnerHTML={{ __html: crestSVG(skin, r.color, r.charge, 44) }} />
        <div className="panel-titles">
          <h2>Barrio en {zone}</h2>
          <p>{atlas ? <><span className="rune">{L.name}</span>, {atlasGloss(r.title)} · </> : L.sub ? `${L.sub} · ` : ''}{plain ? `${t('territory')}: ${L.zone} · ` : ''}barrio n.º {a.ageb}</p>
        </div>
        <button className="close" onClick={onClose} aria-label={t('close')}>✕</button>
      </header>

      <div className="panel-body">
        {!plain && (
          <figure className="portrait-frame">
            <Portrait seed={a.cvegeo} densityRank={rank} color={r.color} skin={skin} />
            <figcaption>{t('portrait_note')}</figcaption>
          </figure>
        )}

        <p className="description">{plain ? describe(a, data.stats) : `“${describe(a, data.stats)}”`}</p>

        {!a.in_census ? (
          <p className="legend-unavailable">{t(data.era === 'antes' ? 'no_census' : 'no_census_now')}</p>
        ) : (
          <>
            <div className="stats-grid">
              <Stat label="personas viven aquí" value={fmt(a.pop)} />
              <Stat label={t('homes')} value={fmt(a.homes)} />
              <Stat label={t('occ')} value={fmt(a.occ, 1)} typ={typS('occ', 1)} />
              <Stat label={t('school')} value={fmt(a.school, 1)} typ={typS('school', 1)} />
              <Stat label={t('per_km2')} value={fmt(a.dens)} typ={typS('dens')} />
              <Stat label={t('area')} value={fmt(a.area_km2, 2)} />
            </div>
            {plain && <p className="wealth-note">«Típico» y la rayita en las barras = el barrio de en medio de {PLACE}: la mitad de los barrios está arriba y la mitad abajo.</p>}

            <h3>{t('ages')}</h3>
            <Bar label={t('a0_14')} value={pct(a.a0_14, a.pop)} color="#c7962f" typ={typ('p_young')} />
            <Bar label={t('a15_64')} value={pct(a.a15_64, a.pop)} color="#c4672f" />
            <Bar label={t('a65')} value={pct(a.a65, a.pop)} color="#7c3f6a" typ={typ('p_old')} />

            <h3>{t('homes_with')}</h3>
            <Bar label={t('inet')} value={a.p_inet} color="#2f8a86" typ={typ('p_inet')} />
            <Bar label={t('car')} value={a.p_car} color="#2f8a86" typ={typ('p_car')} />
            <Bar label={t('pc')} value={a.p_pc} color="#2f8a86" />
            <Bar label={t('water')} value={a.p_water} color="#35607f" />
            <Bar label={t('drain')} value={a.p_drain} color="#35607f" />

            <h3>{t('people')}</h3>
            <Bar label={t('employed')} value={a.p_employed} color="#6f7f3f" />
            <Bar label={t('nohealth')} value={a.p_nohealth} color="#a8462f" />
            <Bar label={t('empty')} value={a.p_empty} color="#8b5a35" />
          </>
        )}

        <h3>{t('wealth')}</h3>
        <div className="wealth-row">
          <span>{t('imu')}</span>
          {a.imu_grade ? (
            <span className={`pill${a.imu_grade === 1 ? ' light' : ''}`} style={{ background: IMU_RAMP[a.imu_grade - 1] }}>{WEALTH_PLAIN[a.imu_grade - 1]}</span>
          ) : (
            <span className="pill muted">{src.conapo_imu2020?.status === 'ok' ? t('no_data') : t('unavailable')}</span>
          )}
        </div>
        <div className="wealth-row">
          <span>{t('grs')}</span>
          {a.grs_grade ? (
            <span className={`pill${a.grs_grade === 1 ? ' light' : ''}`} style={{ background: GRS_RAMP[a.grs_grade - 1] }}>{WEALTH_PLAIN[a.grs_grade - 1]}</span>
          ) : (
            <span className="pill muted">{src.coneval_grs2020?.status === 'ok' ? t('no_data') : t('unavailable')}</span>
          )}
        </div>

        <p className="wealth-note">Mide si la gente tiene escuela, servicio médico, agua, drenaje, internet y otras cosas básicas.</p>

        {data.stats.green && (
          <>
            <h3>Verde</h3>
            {a.ndvi == null ? (
              <p className="legend-note">{t('no_data')}</p>
            ) : (
              <>
                <p className="fauna-line">
                  Hoy: <b>{GREEN_PLAIN[greenClass(data.stats, a.ndvi) ?? 0]}</b>.
                  {a.ndvi_ago != null && Math.abs(a.ndvi / a.ndvi_ago - 1) >= 0.03 && (
                    <> {a.ndvi > a.ndvi_ago ? 'Más' : 'Menos'} verde que hace un año ({a.ndvi > a.ndvi_ago ? '+' : '−'}{fmt(Math.abs(100 * (a.ndvi / a.ndvi_ago - 1)))}%).</>
                  )}
                </p>
                <Bar label="Se ve verde hoy" value={a.p_green ?? null} color="#5a8a4d" />
                <Bar label="Con árboles (2021)" value={a.p_tree ?? null} color="#2f6a3c" />
                <p className="wealth-note">Medido desde satélite. Los árboles salen del mapa ESA WorldCover 2021; no es un conteo de árboles.</p>
              </>
            )}
          </>
        )}

        {data.stats.heat && (
          <>
            <h3>Calor</h3>
            {a.lst == null ? (
              <p className="legend-note">{t('no_data')}</p>
            ) : (
              <>
                <p className="fauna-line">En verano, el suelo de este barrio llega a <b>{fmt(a.lst)} °C</b> a media mañana.</p>
                <Bar label="Más caliente que" value={heatRank} color="#b03426" />
                <p className="wealth-note">Es más caliente que {fmt(heatRank)} de cada 100 barrios. Es la temperatura del suelo y los techos, no del aire.</p>
              </>
            )}
          </>
        )}

        {data.stats.work && a.j_n != null && (
          <>
            <h3>{plain ? 'Empleo' : 'Chamba'}</h3>
            {a.j_n === 0 ? (
              <p className="legend-note">En el directorio de INEGI no hay negocios con local en este barrio.</p>
            ) : (
              <>
                <p className="fauna-line">
                  <b>{WORK_PLAIN[workClass(data.stats, a.j_dens) ?? 0]}</b>. Hay <b>{fmt(a.j_n)}</b> {a.j_n === 1 ? 'negocio' : 'negocios'} y
                  trabajan aquí cerca de <b>{fmt(a.j_emp)}</b> personas.
                  {a.in_census && a.pop != null && a.j_emp! > a.pop * 1.2 && <> Llega a trabajar más gente de la que vive aquí.</>}
                </p>
                <div className="fauna-groups">
                  {WORK_GROUPS.filter(g => (a[`j_${g}` as const] ?? 0) > 0).map(g => (
                    <span key={g} className="fauna-group" title={WORK_INFO[g].name}>
                      <span dangerouslySetInnerHTML={{ __html: workSVG(g, 26, false) }} />
                      {fmt(a[`j_${g}` as const])}
                    </span>
                  ))}
                </div>
                {a.j_top && <p className="legend-note">El más grande: {a.j_top}{a.j_big ? ` (${fmt(a.j_big)} con más de 100 personas)` : ''}.</p>}
                <p className="wealth-note">Los empleos son un cálculo: INEGI da el tamaño de cada negocio en rangos.</p>
              </>
            )}
          </>
        )}

        {data.stats.water && (
          <>
            <h3>{t('m_water')}</h3>
            {a.in_census && (
              <>
                <Bar label={t('water')} value={a.p_water} color="#2f6fa3" typ={typ('p_water')} />
                <Bar label={t('tinaco')} value={a.p_tinaco ?? null} color="#2f6fa3" typ={typ('p_tinaco')} />
                <Bar label={t('cister')} value={a.p_cister ?? null} color="#2f6fa3" typ={typ('p_cister')} />
              </>
            )}
            {a.a_n != null && (
              <p className="fauna-line">
                {a.a_n === 0 ? 'No hay pozos ni tomas con permiso de CONAGUA dentro de este barrio.' : (
                  <>Dentro del barrio hay <b>{fmt(a.a_n)}</b> {a.a_n === 1 ? 'pozo o toma' : 'pozos o tomas'} con permiso para
                    sacar <b>{fmt(a.a_vol)} m³</b> al año{pools(a.a_vol ?? 0) >= 1 ? <> (como {fmt(pools(a.a_vol ?? 0))} albercas olímpicas)</> : null}.</>
                )}
              </p>
            )}
            <p className="wealth-note">Agua entubada, tinaco y cisterna: Censo 2020. Pozos: registro de CONAGUA (lo que permite cada título, no lo que se mide).</p>
          </>
        )}

        {data.stats.campo?.cropland && (
          <>
            <h3>{t('m_campo')}</h3>
            {a.c_crop == null ? (
              <p className="legend-note">{t('no_data')}</p>
            ) : (
              <>
                <Bar label="Se ve sembrado (2021)" value={a.c_crop} color="#5c541e" />
                <p className="wealth-note">Visto desde satélite (ESA WorldCover 2021): qué parte del barrio parece campo sembrado. No es un registro de parcelas.</p>
              </>
            )}
          </>
        )}

        <h3>{t('wildlife')}</h3>
        {a.w_n == null ? (
          <p className="legend-note">{t('unavailable')}</p>
        ) : a.w_n === 0 ? (
          <p className="legend-note">Nadie ha reportado animales en este barrio todavía. ¡Puedes ser el primero con la app iNaturalist!</p>
        ) : (
          <>
            <p className="fauna-line"><b>{fmt(a.w_n)}</b> {a.w_n === 1 ? 'animal reportado' : 'animales reportados'}, de <b>{fmt(a.w_sp)}</b> {a.w_sp === 1 ? 'especie' : 'especies distintas'}.</p>
            <div className="fauna-groups">
              {GROUPS.filter(g => (a[`w_${g}` as const] ?? 0) > 0).map(g => (
                <span key={g} className="fauna-group" title={GROUP_INFO[g].name}>
                  <span dangerouslySetInnerHTML={{ __html: critterSVG(g, 26, false) }} />
                  {fmt(a[`w_${g}` as const])}
                </span>
              ))}
            </div>
            {top.length > 0 && <p className="legend-note">Los más vistos: {top.map(([n]) => n).join(', ')}.</p>}
          </>
        )}

        <p className="panel-sources">
          De dónde salen estos datos: Censo 2020 del INEGI (gente y casas), CONAPO y CONEVAL 2020 (qué tanto le falta a la gente),
          iNaturalist (animales), satélites Landsat (calor), satélites Sentinel-2 y ESA WorldCover (verde), directorio de negocios DENUE del INEGI (chamba), registro de derechos de agua de CONAGUA (agua), ESA WorldCover (campo). Un “—” quiere decir que el INEGI guardó ese dato para proteger la privacidad de pocas familias.
          <br />Clave INEGI del barrio: {a.cvegeo}
        </p>
      </div>
    </aside>
  )
}
