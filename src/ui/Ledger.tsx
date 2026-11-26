import { ModeIcon } from '../art/icons'
import type { CoreData } from '../data'
import { fmt, fmtDate, t } from '../i18n'
import { ATLAS_EPITHET } from '../atlasNames'
import type { Skin } from '../skin'
import { SkinToggle } from './SkinToggle'
import { EraToggle } from './EraToggle'
import type { Era } from '../era'

function Item({ icon, label, value, note, muted }: { icon: React.ReactNode; label: string; value: string; note: string; muted?: boolean }) {
  return (
    <div className={`ledger-item${muted ? ' muted' : ''}`} tabIndex={0}>
      <span className="ledger-icon" aria-hidden="true">{icon}</span>
      <span className="ledger-text">
        <span className="ledger-value">{value}</span>
        <span className="ledger-label">{label}</span>
      </span>
      <span className="ledger-note" role="tooltip">{note}</span>
    </div>
  )
}

/** Libro de cuentas: the top HUD, like a tooled-leather saddlebag strap. */
export function Ledger({ data, skin, setSkin, era, setEra }: { data: CoreData; skin: Skin; setSkin: (s: Skin) => void; era: Era; setEra: (e: Era) => void }) {
  const antes = data.era === 'antes'
  // the 2020 view shows only 2020 numbers: no weekly counters there
  const w = !antes && data.manifest.sources.inaturalist?.status === 'ok' ? data.stats.wildlife : null
  const jb = !antes && data.manifest.sources.inegi_denue?.status === 'ok' ? data.stats.work : null
  const wx = !antes && data.manifest.sources.nasa_power?.status === 'ok' ? data.stats.weather : null
  return (
    <header className="ledger">
      <div className="crest" title={skin === 'atlas' ? `${ATLAS_EPITHET.name}: “${ATLAS_EPITHET.gloss}” (nombre inventado)` : undefined}>
        <span className="crest-title">{t('title')}</span>
        <span className="crest-sub">{t('subtitle')}</span>
      </div>
      <div className="ledger-items">
        {antes ? (
          <Item icon={<ModeIcon id="people" size={22} />} label="Población en 2020" value={fmt(data.stats.municipio.pop)}
            note="Gente que vivía en Juan José Ríos y El Estero en 2020, cuando eran parte de Guasave y Ahome (Censo 2020 del INEGI)" />
        ) : (
          <Item icon={<ModeIcon id="people" size={22} />} label={t('l_pop')} value={data.stats.municipio.pop == null ? t('no_data') : fmt(data.stats.municipio.pop)}
            muted={data.stats.municipio.pop == null}
            note={data.stats.municipio.pop == null
              ? 'El municipio se creó después del Censo 2020: todavía no hay un conteo oficial del municipio. La cifra de 2020 está en «Antes de ser Municipio».'
              : `Gente que vive en el municipio de ${t('title')}, según el INEGI`} />
        )}
        {w && (
          <Item icon={<ModeIcon id="wildlife" size={22} />} label={t('l_wild')} value={fmt(w.week.new)}
            note={`Animales que la gente reportó en iNaturalist del ${fmtDate(w.week.from)} al ${fmtDate(w.week.to)}`} />
        )}
        {wx && (
          <Item icon={<ModeIcon id="heat" size={22} />} label={`Máxima del ${shortDay(wx.latest.date)}`} value={`${fmt(wx.latest.tmax, 0)} °C`}
            note={`Temperatura máxima del aire en ${t('title')} (NASA POWER). Llega con unos días de retraso. La más alta de la semana: ${fmt(wx.week_max.tmax, 0)} °C el ${shortDay(wx.week_max.date)}.`} />
        )}
        {jb && (
          <Item icon={<ModeIcon id="work" size={22} />} label={skin === 'atlas' ? 'talleres y comercios' : skin === 'sencillo' ? 'negocios' : 'lugares de chamba'} value={fmt(jb.total)}
            note={`Negocios con local en el municipio, según el directorio DENUE del INEGI (edición ${jb.edition.slice(5)}/${jb.edition.slice(0, 4)}). Ahí trabajan cerca de ${fmt(Math.round(jb.jobs_est / 1000) * 1000)} personas (cálculo).`} />
        )}
        <Item icon={<ScrollIcon />} label={t('l_refresh')} value={fmtDate(data.manifest.generated)} note="La última vez que se actualizaron los datos" />
      </div>
      <div className="ledger-switches">
        <EraToggle era={era} setEra={setEra} />
        <SkinToggle skin={skin} setSkin={setSkin} />
      </div>
    </header>
  )
}

function ScrollIcon() {
  return (
    <svg viewBox="0 0 32 32" width="22" height="22" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinejoin="round">
      <path d="M8 6h16v18a3 3 0 0 1-3 3H7a3 3 0 0 0 3-3V9a3 3 0 0 0-3-3z" />
      <path d="M13 12h7M13 17h7" strokeLinecap="round" />
    </svg>
  )
}

const shortDay = (iso: string) => new Date(iso + 'T12:00:00').toLocaleDateString('es-MX', { day: 'numeric', month: 'short' })
