import { useEffect, useState } from 'react'
import { Concho, ModeIcon, Seal } from '../art/icons'
import { t } from '../i18n'
import type { Skin } from '../skin'

const KEY = 'hlm-bienvenida-vista'

/** First-visit "¿Cómo se usa?" card, plus a "?" button to open it again. */
export function Welcome({ skin }: { skin: Skin }) {
  const [open, setOpen] = useState(() => localStorage.getItem(KEY) !== '1')
  const close = () => {
    localStorage.setItem(KEY, '1')
    setOpen(false)
  }
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  const touch = window.matchMedia('(hover: none)').matches
  return (
    <>
      <button className="help-btn" onClick={() => setOpen(true)} aria-label="¿Cómo se usa?">?</button>
      {open && (
        <div className="welcome-backdrop" onClick={close}>
          <div className="welcome card" role="dialog" aria-modal="true" aria-labelledby="welcome-title" onClick={e => e.stopPropagation()}>
            <div className="card-head as-title"><span id="welcome-title">¡Bienvenido a Juan José Ríos!</span></div>
            <div className="card-body">
              <p className="welcome-lead">Un mapa de Juan José Ríos hecho con datos reales: cuánta gente vive en cada barrio, qué tanto le falta y qué animales se han visto.</p>
              <ol className="welcome-steps">
                <li>
                  <span className="step-icon concho mini">{skin === 'atlas' ? <Seal /> : skin === 'norteno' ? <Concho /> : null}<ModeIcon id="people" /></span>
                  <span><b>Escoge qué quieres ver</b> con los botones de abajo: gente, bienestar, animales…</span>
                </li>
                <li>
                  <span className="step-icon">🔍</span>
                  <span><b>Acércate</b> {touch ? 'abriendo dos dedos sobre el mapa' : 'con la ruedita del mouse'} para ver cada barrio y hasta cada manzana.</span>
                </li>
                <li>
                  <span className="step-icon">👆</span>
                  <span><b>{touch ? 'Toca' : 'Haz clic en'} un barrio</b> para ver su ficha con todos sus datos.</span>
                </li>
                <li>
                  <span className="step-icon">📅</span>
                  <span><b>Escoge la época</b> arriba: <i>{t('era_municipio')}</i> (los barrios de hoy y datos que se actualizan) o <i>{t('era_antes')}</i> (2020, cuando era parte de Guasave, con los números del censo).</span>
                </li>
                <li>
                  <span className="step-icon">🗺️</span>
                  <span><b>Cambia el estilo</b> del mapa arriba: <i>{t('skin_sencillo')}</i>, <i>{t('skin_norteno')}</i> o <i>{t('skin_atlas')}</i>. Los datos son los mismos.</span>
                </li>
              </ol>
              <p className="legend-note">Todos los números son reales y dicen de dónde salen. Si un dato no existe, el mapa lo dice en lugar de inventarlo.</p>
              <button className="welcome-go" onClick={close} autoFocus>{t('welcome_go')}</button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
