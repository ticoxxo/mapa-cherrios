import { useEffect, useRef } from 'react'
import { Concho, LockIcon, ModeIcon, Seal } from '../art/icons'
import type { Skin } from '../skin'
import type { Manifest } from '../data'
import type { Era } from '../era'
import { t } from '../i18n'
import { MODES, modeState, type ModeId } from '../modes'

/** Map modes as silver conchos on a leather belt. */
export function ModeBar({ manifest, era, mode, setMode, skin }: { manifest: Manifest; era: Era; mode: ModeId; setMode: (m: ModeId) => void; skin: Skin }) {
  // on phones the belt scrolls sideways: keep the chosen mode in view (also when chosen with the keyboard)
  const nav = useRef<HTMLElement>(null)
  useEffect(() => {
    const bar = nav.current
    const btn = bar?.querySelector<HTMLElement>('.mode-btn.active')
    if (!bar || !btn || bar.scrollWidth <= bar.clientWidth) return
    const l = btn.offsetLeft, r = l + btn.offsetWidth
    if (l < bar.scrollLeft) bar.scrollTo({ left: l - 8, behavior: 'smooth' })
    else if (r > bar.scrollLeft + bar.clientWidth) bar.scrollTo({ left: r - bar.clientWidth + 8, behavior: 'smooth' })
  }, [mode])
  return (
    <nav ref={nav} className="modebar" aria-label="Modos del mapa">
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
