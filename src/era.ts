// Two views of the same town:
//   municipio → Juan José Ríos as a municipio (2025 zones) with the data that keeps updating (default)
//   antes     → "Antes de ser Municipio": 2020, when the town belonged to Guasave (and El Estero to Ahome),
//               on the 2020 zones with the 2020 census. Only data from 2020 is shown there.
// `?era=antes` opens the old view; the choice is saved per browser.
import { useState } from 'react'
import type { ModeId } from './modes'

export type Era = 'municipio' | 'antes'
export const ERAS: Era[] = ['municipio', 'antes']

/** Modes that have 2020 data on the 2020 zones. Everything else is current data only. */
export const ANTES_MODES: ModeId[] = ['realm', 'people', 'wealth']

const KEY = 'jjr-era'
const isEra = (x: unknown): x is Era => ERAS.includes(x as Era)

export function readEra(): Era {
  try {
    const q = new URLSearchParams(window.location.search).get('era')
    if (isEra(q)) return q
    const s = localStorage.getItem(KEY)
    if (isEra(s)) return s
  } catch {
    /* private mode etc. */
  }
  return 'municipio'
}

export function useEra(): [Era, (e: Era) => void] {
  const [era, setState] = useState<Era>(readEra)
  const set = (e: Era) => {
    try {
      localStorage.setItem(KEY, e)
      const u = new URL(window.location.href)
      if (e === 'antes') u.searchParams.set('era', e)
      else u.searchParams.delete('era')
      history.replaceState(null, '', u)
    } catch {
      /* ignore */
    }
    setState(e)
  }
  return [era, set]
}
