import type { ModeId } from '../modes'

const c = 'currentColor'
const p = { fill: 'none', stroke: c, strokeWidth: 2.2, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const }

const ICONS: Record<ModeId, React.ReactNode> = {
  realm: (
    <>
      <path d="M5 24h22l2-13-7 5-6-9-6 9-7-5z" {...p} fill={c} fillOpacity={0.18} />
      <circle cx="16" cy="6" r="1.8" fill={c} />
      <path d="M8 28h16" {...p} />
    </>
  ),
  people: (
    <>
      <circle cx="11" cy="10" r="4" {...p} />
      <circle cx="22" cy="12" r="3.2" {...p} />
      <path d="M3.5 27c.5-6 3.5-9 7.5-9s7 3 7.5 9M17 26c.4-4 2.4-7 5-7s4.6 3 5 7" {...p} />
    </>
  ),
  wealth: (
    <>
      <ellipse cx="16" cy="9" rx="9" ry="3.5" {...p} fill={c} fillOpacity={0.18} />
      <path d="M7 9v6c0 2 4 3.5 9 3.5s9-1.5 9-3.5V9M7 15v6c0 2 4 3.5 9 3.5s9-1.5 9-3.5v-6" {...p} />
    </>
  ),
  heat: (
    <>
      <circle cx="16" cy="16" r="5.5" {...p} fill={c} fillOpacity={0.18} />
      {Array.from({ length: 8 }, (_, i) => {
        const a = (i * Math.PI) / 4
        return <path key={i} d={`M${16 + Math.cos(a) * 9} ${16 + Math.sin(a) * 9}L${16 + Math.cos(a) * 12.5} ${16 + Math.sin(a) * 12.5}`} {...p} />
      })}
    </>
  ),
  green: (
    <>
      <path d="M16 29V15" {...p} />
      <path d="M16 4c6 3 8 8 7 12-1 3-4 4-7 4s-6-1-7-4c-1-4 1-9 7-12z" {...p} fill={c} fillOpacity={0.18} />
      <path d="M12 26h8" {...p} />
    </>
  ),
  wildlife: (
    <>
      <path d="M4 14c4-5 8-5 12 0 4-5 8-5 12 0-4-1.5-8-.5-12 4-4-4.5-8-5.5-12-4z" {...p} fill={c} fillOpacity={0.18} />
      <path d="M9 24c2-2 4-2 6 0M17 26c2-2 4-2 6 0" {...p} />
    </>
  ),
  water: (
    <>
      <path d="M16 4c5 7 9 11.5 9 16a9 9 0 0 1-18 0c0-4.5 4-9 9-16z" {...p} fill={c} fillOpacity={0.18} />
      <path d="M11.5 20.5a4.5 4.5 0 0 0 4 4.4" {...p} />
    </>
  ),
  campo: (
    <>
      <path d="M3 27 13 14M10 27l6-13M17 27l2-13M24 27l-3-13M29 27l-8-13" {...p} />
      <path d="M16 11V4M16 8c-2.5 0-4-1.5-4.5-4 2.5 0 4 1.5 4.5 4zm0-1.5c2.5 0 4-1.5 4.5-4-2.5 0-4 1.5-4.5 4z" {...p} fill={c} fillOpacity={0.18} />
    </>
  ),
  work: (
    <>
      <path d="M4 27V15l6 4v-4l6 4v-4l6 4V7h5v20z" {...p} fill={c} fillOpacity={0.18} />
      <path d="M8 27v-4M14 27v-4M20 27v-4" {...p} />
    </>
  ),
}

export function ModeIcon({ id, size = 26 }: { id: ModeId; size?: number }) {
  return (
    <svg viewBox="0 0 32 32" width={size} height={size} aria-hidden="true">
      {ICONS[id]}
    </svg>
  )
}

export function LockIcon() {
  return (
    <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
      <rect x="3" y="7" width="10" height="7" rx="1.5" fill="currentColor" />
      <path d="M5 7V5a3 3 0 0 1 6 0v2" fill="none" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  )
}

/** Scalloped silver concho (belt/saddle ornament) behind each mode icon. */
const SCALLOP = (() => {
  const n = 16, R = 30, r = 3.6
  let d = ''
  for (let i = 0; i < n; i++) {
    const a0 = (i / n) * Math.PI * 2, a1 = ((i + 1) / n) * Math.PI * 2
    const p0 = [32 + Math.cos(a0) * R, 32 + Math.sin(a0) * R]
    const p1 = [32 + Math.cos(a1) * R, 32 + Math.sin(a1) * R]
    d += `${i ? '' : `M${p0[0].toFixed(2)} ${p0[1].toFixed(2)}`}A${r} ${r} 0 0 1 ${p1[0].toFixed(2)} ${p1[1].toFixed(2)}`
  }
  return d + 'Z'
})()

export function Concho() {
  return (
    <svg className="concho-svg" viewBox="0 0 64 64" aria-hidden="true">
      <defs>
        <radialGradient id="plata" cx=".38" cy=".32" r=".8">
          <stop offset="0" stopColor="#ffffff" />
          <stop offset=".45" stopColor="#cfcac0" />
          <stop offset="1" stopColor="#7d776c" />
        </radialGradient>
        <radialGradient id="turquesa" cx=".4" cy=".35" r=".75">
          <stop offset="0" stopColor="#9fe3d6" />
          <stop offset=".6" stopColor="#2f9c95" />
          <stop offset="1" stopColor="#1d5f5b" />
        </radialGradient>
      </defs>
      <path d={SCALLOP} fill="url(#plata)" stroke="#3b3229" strokeWidth="1.4" />
      <circle cx="32" cy="32" r="24" fill="none" stroke="#6d665b" strokeWidth="1" strokeDasharray="1.5 2.5" />
      <circle cx="32" cy="32" r="20" className="concho-stone" stroke="#3b3229" strokeWidth="1.4" />
    </svg>
  )
}

// Wax seal for the Atlas skin: a slightly irregular blob with a pressed inner ring.
const BLOB = (() => {
  const n = 14
  let d = ''
  for (let i = 0; i <= n; i++) {
    const a = (i / n) * Math.PI * 2
    const r = 28 + (i % 2 ? 1.6 : -0.6) + Math.sin(i * 2.3) * 1.2
    d += `${i ? 'L' : 'M'}${(32 + Math.cos(a) * r).toFixed(2)} ${(32 + Math.sin(a) * r).toFixed(2)}`
  }
  return d + 'Z'
})()

export function Seal() {
  return (
    <svg className="concho-svg seal-svg" viewBox="0 0 64 64" aria-hidden="true">
      <defs>
        <radialGradient id="cera" cx=".38" cy=".32" r=".85">
          <stop offset="0" stopColor="#c4584a" />
          <stop offset=".55" stopColor="#8e2a22" />
          <stop offset="1" stopColor="#4e1410" />
        </radialGradient>
        <radialGradient id="cera-oro" cx=".38" cy=".32" r=".85">
          <stop offset="0" stopColor="#f3dc8e" />
          <stop offset=".55" stopColor="#c09a3e" />
          <stop offset="1" stopColor="#6e5418" />
        </radialGradient>
      </defs>
      <path d={BLOB} className="seal-wax" stroke="#2b1a10" strokeWidth="1.2" strokeLinejoin="round" />
      <circle cx="32" cy="32" r="21" fill="none" stroke="#000" strokeOpacity=".35" strokeWidth="2.4" />
      <circle cx="32" cy="32" r="21" fill="none" stroke="#fff" strokeOpacity=".22" strokeWidth=".8" transform="translate(.6 .8)" />
    </svg>
  )
}
