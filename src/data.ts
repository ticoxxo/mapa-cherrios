import type { Era } from './era'

// Loads the static outputs of /pipeline. Every number shown in the UI comes from these files.

export type LayerStatus = 'ok' | 'unavailable' | 'not_built' | 'partial'

export interface Source {
  id: string
  name: string
  url: string
  license: string
  publisher: string
  vintage: string
  retrieved: string
  status: LayerStatus
  notes: string
  modeled: boolean
}

export interface Manifest {
  generated: string
  sources: Record<string, Source>
  layers: Record<string, { status: LayerStatus; sources: string[]; [k: string]: unknown }>
}

export interface WildStats {
  total: number
  excluded_unlicensed: number
  obscured: number
  placed: number
  in_ageb: number
  species: number
  groups: Record<string, number>
  week: { from: string; to: string; new: number; groups: Record<string, number>; top: string[]; firsts: [string, string][] }
}

export interface GreenStats {
  window: [string, string]
  scenes_now: string[]
  scenes_ago: string[]
  city_ndvi: number
  city_p_green: number
  city_ndvi_ago: number | null
  city_p_tree: number
  n_trees: number
}

export interface HeatStats {
  scenes: string[]
  n_scenes: number
  summers: number[]
  ageb_min: number
  ageb_max: number
  ageb_median: number
  hottest: { cvegeo: string; lst: number }[]
  image?: { file: string; bounds: [number, number, number, number]; range: [number, number] }
}

export interface Stats {
  /** which view these numbers belong to (see src/era.ts) */
  era?: 'municipio' | 'antes'
  /** "antes": municipio each 2020 census code belonged to, e.g. { "011": "Guasave" } */
  parent?: Record<string, string>
  municipio: { pop: number | null; homes: number | null }
  city: { name: string; pop: number | null; area_km2: number }
  localities: Record<string, { name: string; pop: number }>
  n_ageb: number
  n_ageb_without_census: number
  breaks: { dens: number[]; w_n?: number[]; lst?: number[]; ndvi?: number[]; j_dens?: number[]; p_tinaco?: number[] }
  work?: WorkStats | null
  water?: WaterStats | null
  green?: GreenStats | null
  wildlife?: WildStats | null
  heat?: HeatStats | null
  weather?: { latest: { date: string; tmax: number }; week_max: { date: string; tmax: number }; series: { date: string; tmax: number }[] } | null
  ranges: Record<string, [number, number, number]>
}

/** Properties of one AGEB feature (see pipeline/hlm/run.py). null = not available. */
export interface Ageb {
  cvegeo: string
  loc: string
  /** "antes" view only: 2020 municipio code (011 Guasave, 001 Ahome) */
  mun?: string
  ageb: string
  realm: string
  color: string
  area_km2: number
  in_census: boolean
  pop: number | null
  fem: number | null
  mas: number | null
  a0_14: number | null
  a15_64: number | null
  a65: number | null
  school: number | null
  pea: number | null
  employed: number | null
  homes: number | null
  dwell: number | null
  empty: number | null
  occ: number | null
  dens: number | null
  p_young: number | null
  p_old: number | null
  p_inet: number | null
  p_car: number | null
  p_pc: number | null
  p_water: number | null
  p_drain: number | null
  p_tinaco?: number | null
  p_cister?: number | null
  p_nohealth: number | null
  p_empty: number | null
  p_employed: number | null
  imu_grade: number | null
  imu: number | null
  grs_grade: number | null
  w_n?: number | null
  w_sp?: number | null
  w_ave?: number | null
  w_rep?: number | null
  w_mam?: number | null
  w_ins?: number | null
  w_otr?: number | null
  w_top?: string | null
  lst?: number | null
  ndvi?: number | null
  p_green?: number | null
  ndvi_ago?: number | null
  p_tree?: number | null
  j_n?: number
  j_emp?: number
  j_dens?: number | null
  j_big?: number
  j_top?: string | null
  j_tienda?: number
  j_comida?: number
  j_taller?: number
  j_oficina?: number
  j_fabrica?: number
  j_escuela?: number
  a_n?: number
  a_vol?: number
}

/** INEGI DENUE summary for the municipio (see pipeline/hlm/work.py). */
export interface WorkStats {
  edition: string
  published: string
  total: number
  jobs_est: number
  groups: Record<string, number>
  sizes: number[]
  new_year: { year: string; total: number; groups: Record<string, number> }
  n_big: number
  jobs_mid: number[]
}

/** Agua: CONAGUA REPDA water rights + SMN drought monitor (see pipeline/hlm/water.py). */
export interface WaterStats {
  rights: {
    snapshot: string // yyyy-mm of the REPDA release
    last_registration: string
    n: number
    n_wells: number
    n_intakes: number
    hm3: number
    uses: Record<string, number> // millions of m³ per year
    aquifers: [string, number, number][] // name, points, hm³
    top: [string, number][]
    particular_hm3: number
  } | null
  drought: {
    date: string
    level: number // 0 sin sequía, 1 D0 … 5 D4
    since: string
    worst_year: number | null
    worst_ever: [string, number]
    series: [string, number][]
  } | null
}

/** One well or surface intake from REPDA as drawn on the map. */
export interface Well {
  k: 0 | 1 // 0 pozo, 1 toma superficial
  u: import('./art/water').WaterUse
  v: number // m³ per year the title authorises
  aq: string | null
  h: string // holder; '' = private person (not named)
  y: string // year the title was registered
  d: 0 | 1 // inside the irrigation district
}

/** One business from DENUE as drawn on the map. */
export interface Biz {
  g: import('./art/work').WorkGroup
  s: number // size class index, -1 unknown
  n: string
  c: string // SCIAN code
  a: string // yyyy-mm it entered the directory
  act?: string
}

/** One iNaturalist sighting on the map (see pipeline/hlm/wildlife.py). */
export interface Sighting {
  i: number
  g: 'ave' | 'rep' | 'mam' | 'ins' | 'otr'
  n: string
  s: string
  d: string | null
  u: string | null
  l: string
  w: 0 | 1
}

export interface Realm {
  id: string
  name: string | null
  title: string
  name_basis: string
  color: string
  charge: string
  pop: number
  area_km2: number
  dens: number | null
  n_ageb: number
  label: [number, number]
  imu_grade_avg: number | null
}

export interface Chronicle {
  entries: { date: string; kind: string; title?: string; es: string; source?: string }[]
}

const BASE = import.meta.env.BASE_URL + 'data/'

async function getJSON<T>(name: string): Promise<T | null> {
  try {
    const r = await fetch(BASE + name)
    if (!r.ok) return null
    return (await r.json()) as T
  } catch {
    return null
  }
}

export interface CoreData {
  era: Era
  /** folder of this view's files: '' (municipio) or 'antes/' */
  dir: string
  manifest: Manifest
  stats: Stats
  realms: GeoJSON.FeatureCollection
  agebs: GeoJSON.FeatureCollection
  chronicle: Chronicle | null
}

/** The manifest and La Gaceta are shared; zones, territorios and numbers come from the view's folder. */
export async function loadCore(era: Era): Promise<CoreData> {
  const dir = era === 'antes' ? 'antes/' : ''
  const [manifest, stats, realms, agebs, chronicle] = await Promise.all([
    getJSON<Manifest>('manifest.json'),
    getJSON<Stats>(dir + 'stats.json'),
    getJSON<GeoJSON.FeatureCollection>(dir + 'realms.geojson'),
    getJSON<GeoJSON.FeatureCollection>(dir + 'agebs.geojson'),
    getJSON<Chronicle>('chronicle.json'),
  ])
  if (!manifest || !stats || !realms || !agebs) throw new Error('core data missing — run the pipeline')
  return { era, dir, manifest, stats, realms, agebs, chronicle }
}

export const dataUrl = (name: string) => new URL(BASE + name, window.location.href).toString()
