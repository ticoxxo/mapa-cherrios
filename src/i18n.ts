import { getSkin } from './skin'

// Interfaz solo en español de México, con vocabulario norteño.
//   Territorio  = agrupación visual de AGEB (reino)
//   Comarca     = territorio del anillo interior · Frontera = anillo exterior
//   Barrio      = una AGEB urbana · Manzana = una manzana del INEGI

/** The town this map is about (Sinaloa, municipio 25-020 since 2021). */
export const PLACE = 'Juan José Ríos'

export const T = {
  title: PLACE,
  subtitle: 'El Mapa Vivo',
  // modos
  m_realm: 'Territorio',
  m_people: 'Gente',
  m_wealth: 'Bienestar',
  m_heat: 'Calor',
  m_green: 'Verde',
  m_wildlife: 'Fauna',
  m_work: 'Chamba',
  m_water: 'Agua',
  m_campo: 'Campo',
  soon: 'Próximamente',
  unavailable: 'Datos no disponibles',
  // libro de cuentas (HUD)
  l_pop: 'Población',
  l_jobs: 'Empleos con IMSS',
  l_temp: 'Calor de hoy',
  l_wild: 'Animales esta semana',
  l_refresh: 'Actualizado',
  l_notyet: 'todavía no lo agregamos',
  // ficha del barrio
  barrio: 'Barrio',
  inhabitants: 'habitantes',
  per_km2: 'personas por km²',
  area: 'Tamaño (km²)',
  homes: 'Casas con gente',
  occ: 'Personas por casa',
  school: 'Años de escuela, en promedio',
  ages: 'Edades',
  a0_14: '0 a 14 años',
  a15_64: '15 a 64 años',
  a65: '65 y más',
  homes_with: 'Hogares con…',
  inet: 'Internet',
  car: 'Troca o carro',
  pc: 'Computadora',
  water: 'Agua entubada',
  tinaco: 'Tinaco',
  cister: 'Cisterna o aljibe',
  drain: 'Drenaje',
  people: 'Gente',
  nohealth: 'Sin servicio médico',
  employed: 'Con trabajo (de quienes trabajan o buscan)',
  empty: 'Casas vacías',
  wealth: 'Bienestar',
  imu: 'Qué tanto le falta (CONAPO)',
  grs: 'Qué tanto le falta (CONEVAL)',
  no_census: 'Este barrio es nuevo: no existía en el Censo 2020, así que todavía no hay cifras.',
  sources: 'Fuentes',
  close: 'Cerrar',
  realm_note: 'Los territorios y sus nombres son de este mapa; no son divisiones oficiales.',
  portrait_note: 'Dibujo hecho a partir de cuánta gente vive aquí.',
  chronicle: 'La Gaceta',
  legend: 'Leyenda',
  credits: 'Créditos de datos',
  no_data: 'Sin datos',
  loading: 'Desenrollando el mapa…',
  load_error: 'No se pudo cargar el mapa. Intenta de nuevo en un rato.',
  territory: 'Territorio',
  click_hint: 'Haz clic para ver todo sobre este barrio',
  census_2020: 'Censo 2020',
  wildlife: 'Animales vistos aquí',
  // selector de estilo
  skin_label: 'Estilo del mapa',
  skin_sencillo: 'Sencillo',
  skin_norteno: 'Norteño',
  skin_atlas: 'Atlas antiguo',
  welcome_go: '¡Órale, vamos!',
  // épocas: municipio de hoy vs. antes de ser municipio (Censo 2020, parte de Guasave)
  era_label: 'Época del mapa',
  era_municipio: 'Municipio',
  era_antes: 'Antes de ser Municipio',
  era_municipio_hint: 'Juan José Ríos como municipio: barrios de hoy y datos que se actualizan',
  era_antes_hint: 'Cómo era en 2020, cuando Juan José Ríos era parte de Guasave (Censo 2020)',
  only_antes: 'Estos datos son del Censo 2020, de cuando Juan José Ríos todavía era parte de Guasave. El INEGI cambió los barrios al hacerse municipio, así que esos números no se pueden poner en los barrios de hoy.',
  only_municipio: 'Estos son datos de hoy. En la vista de 2020 solo va lo que se midió en 2020.',
  see_antes: 'Ver «Antes de ser Municipio»',
  see_municipio: 'Ver el Municipio de hoy',
  antes_note: 'Así era en 2020: Juan José Ríos era parte del municipio de Guasave y El Estero, de Ahome. Los barrios son los del Censo 2020.',
  no_census_now: 'Este barrio es de cuando ya era municipio. El último censo (2020) usaba otros barrios: sus números están en «Antes de ser Municipio».',
} as const

export type Key = keyof typeof T

/** Atlas skin: same meaning, old-atlas wording. Anything missing falls back to T. */
const T_ATLAS: Partial<Record<Key, string>> = {
  subtitle: 'El Atlas Vivo',
  m_realm: 'Reinos',
  m_people: 'Gentes',
  m_wildlife: 'Criaturas',
  m_green: 'Verdor',
  m_work: 'Oficios',
  m_water: 'Aguas',
  m_campo: 'Labranzas',
  car: 'Carro',
  territory: 'Reino',
  chronicle: 'Los Anales',
  legend: 'Leyenda del mapa',
  loading: 'Desplegando el pergamino…',
  realm_note: 'Los reinos y sus nombres antiguos son inventados para este mapa; no son divisiones oficiales. Abajo de cada nombre va su significado y el nombre real del lugar.',
  welcome_go: '¡Adelante!',
}

/** Sencillo skin: plain, everyday words. Anything missing falls back to T. */
const T_SENCILLO: Partial<Record<Key, string>> = {
  m_realm: 'Zonas',
  m_wildlife: 'Animales',
  m_work: 'Empleo',
  territory: 'Zona',
  car: 'Auto',
  chronicle: 'Novedades',
  loading: 'Cargando el mapa…',
  realm_note: 'Las zonas son grupos de barrios hechos para este mapa; no son divisiones oficiales.',
  welcome_go: 'Empezar',
}

const BY_SKIN = { sencillo: T_SENCILLO, atlas: T_ATLAS, norteno: {} as Partial<Record<Key, string>> }

export const t = (k: Key): string => BY_SKIN[getSkin()][k] ?? T[k]

export const fmt = (n: number | null | undefined, digits = 0) =>
  n == null ? '—' : n.toLocaleString('es-MX', { maximumFractionDigits: digits })

export const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString('es-MX', { day: 'numeric', month: 'short', year: 'numeric' })

/** "San Pedro o el Saucito (San Pedro el Saucito)" → "San Pedro o el Saucito" */
export const shortName = (n: string | null) => (n ? n.replace(/\s*\(.*\)\s*$/, '') : null)
