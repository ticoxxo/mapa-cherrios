// Short, plain description of a barrio, built only from its real census statistics.
import type { Ageb, Stats } from './data'

export function describe(a: Ageb, s: Stats): string {
  // today's zones (municipio view) have no census figures: describe them only with what is measured now
  const now = s.era === 'municipio' && !a.in_census
  if (!now && (!a.in_census || a.pop == null)) return 'Tierra nueva: el Censo 2020 todavía no la registraba.'
  if (!now && a.pop === 0) return 'Tierra sin habitantes censados en 2020.'

  const med = (k: string) => s.ranges[k]?.[2]
  const parts: string[] = []
  const dens = a.dens ?? 0
  const dm = med('dens') ?? 0
  if (now) parts.push('Barrio del municipio de hoy')
  else if (dens > dm * 1.6) parts.push('Barrio bien apretado de gente')
  else if (dens < dm * 0.5) parts.push('Barrio despoblado, de casas regadas')
  else parts.push('Barrio de densidad típica del pueblo')

  if (a.p_young != null && a.p_young > (med('p_young') ?? 99) + 5) parts.push('muchas familias jóvenes')
  if (a.p_old != null && a.p_old > (med('p_old') ?? 99) * 1.6) parts.push('muchos adultos mayores')
  if (a.school != null && a.school >= 13) parts.push('mucha escuela')
  if (a.school != null && a.school < 9) parts.push('poca escuela')
  if (a.p_car != null && a.p_car < 55) parts.push('pocos hogares con troca o carro')
  if (a.p_inet != null && a.p_inet < 45) parts.push('poco internet')
  if (a.p_empty != null && a.p_empty > 20) parts.push('muchas casas solas')
  if (a.imu_grade != null && a.imu_grade >= 4) parts.push('carencias en lo básico')
  if (a.imu_grade != null && a.imu_grade <= 1) parts.push('casi sin carencias')
  if (a.w_n != null && a.w_n >= 18) parts.push('muchos animales reportados')
  if (a.p_tree != null && a.p_tree >= 15) parts.push('muchos árboles')
  if (a.p_tree != null && a.p_tree < 0.5 && (a.pop ?? 0) > 0) parts.push('casi sin árboles')
  if (a.j_emp != null && a.pop && a.j_emp > a.pop * 2) parts.push('más chamba que vecinos')
  const hb = s.breaks.lst ?? []
  if (a.lst != null && hb.length && a.lst >= hb[hb.length - 1]) parts.push('suelo de los más calientes en verano')
  if (a.lst != null && hb.length && a.lst < hb[0]) parts.push('suelo de los más frescos en verano')

  const rest = parts.slice(1, 4)
  const join = (xs: string[]) => (xs.length <= 1 ? xs.join('') : xs.slice(0, -1).join(', ') + ' y ' + xs[xs.length - 1])
  return rest.length ? `${parts[0]}, con ${join(rest)}.` : `${parts[0]}.`
}
