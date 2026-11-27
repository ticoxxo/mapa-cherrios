import { useState } from 'react'
import type { Manifest } from '../data'
import { fmtDate, t } from '../i18n'

const ALWAYS = ['INEGI', 'CONAPO', 'CONEVAL', 'CONAGUA', 'SMN', 'SIAP', 'CONABIO', '© colaboradores de OpenStreetMap (ODbL)', 'ESA', 'USGS/NASA', 'Copernicus', 'iNaturalist', 'Natural Earth']

export function Credits({ manifest }: { manifest: Manifest }) {
  const [open, setOpen] = useState(false)
  return (
    <footer className={`credits${open ? ' open' : ''}`}>
      <button onClick={() => setOpen(!open)} aria-expanded={open}>
        {t('credits')}: {ALWAYS.join(' · ')}
      </button>
      {open && (
        <div className="credits-body card" role="dialog" aria-label={t('credits')}>
          <table>
            <thead>
              <tr><th>Fuente</th><th>Edición</th><th>Licencia</th><th>Obtenido</th><th>Estado</th></tr>
            </thead>
            <tbody>
              {Object.values(manifest.sources).map(s => (
                <tr key={s.id} className={s.status}>
                  <td>
                    <a href={s.url.startsWith('http') ? s.url : undefined} target="_blank" rel="noreferrer">{s.publisher} — {s.name}</a>
                    {s.modeled && <em> (derivado/modelado)</em>}
                  </td>
                  <td>{s.vintage}</td>
                  <td>{s.license}</td>
                  <td>{fmtDate(s.retrieved)}</td>
                  <td>{s.status === 'ok' ? '✓' : s.status === 'partial' ? 'parcial' : t('unavailable')}</td>
                </tr>
              ))}
              <tr>
                <td>Mapzen / AWS Terrain Tiles — relieve</td>
                <td>SRTM, ETOPO1, USGS</td>
                <td>varias, con atribución</td>
                <td>en vivo</td>
                <td>✓</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </footer>
  )
}
