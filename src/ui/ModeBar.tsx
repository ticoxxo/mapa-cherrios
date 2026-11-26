import { Concho, LockIcon, ModeIcon, Seal } from '../art/icons'
import type { Skin } from '../skin'
import type { Manifest } from '../data'
import type { Era } from '../era'
import { t } from '../i18n'
import { MODES, modeState, type ModeId } from '../modes'

/** Map modes as silver conchos on a leather belt. */
export function ModeBar({ manifest, era, mode, setMode, skin }: { manifest: Manifest; era: Era; mode: ModeId; setMode: (m: ModeId) => void; skin: Skin }) {
  return (
    <nav className="modebar" aria-label="Modos del mapa">
      {MODES.map((m, i) => {
        const st = modeState(manifest, m.id, era)
        const label = t(m.label)
        const sub = st === 'soon' ? t('soon') : st === 'unavailable' ? t('unavailable')
          : st === 'only_antes' ? `solo en «${t('era_antes')}»` : st === 'only_municipio' ? `solo en «${t('era_municipio')}»` : ''
        return (
          <button
            key={m.id}
            className={`mode-btn mode-${m.id}${mode === m.id ? ' active' : ''} ${st}`}
            onClick={() => setMode(m.id)}
            aria-pressed={mode === m.id}
            aria-label={sub ? `${label} — ${sub}` : label}
            title={`${m.hint}${sub ? ` (${sub.toLowerCase()})` : ''} · tecla ${i + 1}`}
          >
            <span className="concho">
              {skin === 'atlas' ? <Seal /> : skin === 'norteno' ? <Concho /> : null}
              <ModeIcon id={m.id} />
              {st !== 'ok' && <span className="mode-lock"><LockIcon /></span>}
            </span>
            <span className="mode-label">{label}</span>
          </button>
        )
      })}
    </nav>
  )
}
