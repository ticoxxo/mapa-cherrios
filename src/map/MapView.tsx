import { useEffect, useRef } from 'react'
import maplibregl, { type Map as MLMap, type MapGeoJSONFeature } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { baseStyle, PALETTES, SKIN_PAINT } from './style'
import type { Skin } from '../skin'
import { dataUrl, type Ageb, type Biz, type CoreData, type Field, type Realm, type Sighting, type Well } from '../data'
import { blockPeopleColorExpr, CAMPO_KIND, campoColorExpr, greenColorExpr, heatColorExpr, peopleColorExpr, waterColorExpr, wealthColorExpr, wildlifeColorExpr, workColorExpr, type ModeId } from '../modes'
import { addCritterImages, critterSVG, type Group } from '../art/critters'
import { addTreeImage } from '../art/trees'
import { addWorkImages, WORK_GROUPS, type WorkGroup } from '../art/work'
import { addWaterImages, WATER_USES, type WaterUse } from '../art/water'
import { realmBannerSVG } from '../art/heraldry'
import { realmLabel } from '../atlasNames'
import { tokenMinZoom, tokenSVG } from '../art/tokens'

export type Tier = 'realm' | 'county' | 'block'
// a small town: territorios only when zoomed well out
export const tierOf = (z: number): Tier => (z < 12.6 ? 'realm' : z < 14.2 ? 'county' : 'block')

export interface SightingInfo {
  x: number
  y: number
  s?: Sighting
  b?: Biz
  well?: Well
  field?: Field
  pinned: boolean
}

export interface HoverInfo {
  x: number
  y: number
  ageb: Ageb
  realm: Realm
}

interface Props {
  data: CoreData
  mode: ModeId
  skin: Skin
  wealthPrimary: 'imu' | 'grs' | null
  selected: string | null
  onHover: (h: HoverInfo | null) => void
  onSelect: (cvegeo: string | null) => void
  onTier: (t: Tier) => void
  groups: Set<Group>
  workGroups: Set<WorkGroup>
  waterUses: Set<WaterUse>
  onSighting: (s: SightingInfo | null, explicit?: boolean) => void
}

const FILL_MODES: ModeId[] = ['realm', 'people', 'wealth', 'wildlife', 'heat', 'green', 'work', 'water', 'campo']
// per-mode opacity at zoom 9 / 12 / 15 (multiplied by the crossfade weight)
const OPACITY: Record<string, [number, number, number]> = {
  realm: [0.78, 0.5, 0.22],
  people: [0.88, 0.82, 0.55],
  wealth: [0.88, 0.82, 0.55],
  wildlife: [0.8, 0.7, 0.35],
  heat: [0.88, 0.8, 0.3],
  green: [0.85, 0.75, 0.4],
  work: [0.88, 0.8, 0.35],
  water: [0.85, 0.75, 0.35],
  campo: [0.7, 0.6, 0.35],
}
const opacityExpr = (m: string, k: number) =>
  ['interpolate', ['linear'], ['zoom'], 9, OPACITY[m][0] * k, 12, OPACITY[m][1] * k, 15, OPACITY[m][2] * k] as unknown as number

export function MapView({ data, mode, skin, wealthPrimary, selected, onHover, onSelect, onTier, groups, workGroups, waterUses, onSighting }: Props) {
  const el = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MLMap | null>(null)
  const weights = useRef<Record<string, number>>({ realm: 1, people: 0, wealth: 0, wildlife: 0, heat: 0, green: 0, work: 0, water: 0, campo: 0 })
  const anim = useRef<number>(0)
  const banners = useRef<{ m: maplibregl.Marker; r: Realm }[]>([])
  const cb = useRef({ onHover, onSelect, onTier, onSighting })
  cb.current = { onHover, onSelect, onTier, onSighting }
  const liveMarkers = useRef<{ m: maplibregl.Marker; g: Group }[]>([])
  const heatMarkers = useRef<maplibregl.Marker[]>([])
  const wildState = useRef<'none' | 'loading' | 'ready'>('none')
  const skinRef = useRef(skin)
  skinRef.current = skin
  const modeRef = useRef(mode)
  modeRef.current = mode
  const groupsRef = useRef(groups)
  groupsRef.current = groups
  const workGroupsRef = useRef(workGroups)
  workGroupsRef.current = workGroups
  const waterUsesRef = useRef(waterUses)
  waterUsesRef.current = waterUses

  // ---------- create map once ----------
  useEffect(() => {
    if (!el.current) return
    const realmsById = new Map<string, Realm>()
    for (const f of data.realms.features) realmsById.set((f.properties as Realm).id, f.properties as Realm)

    const INK = PALETTES[skinRef.current].ink
    const map = new maplibregl.Map({
      container: el.current,
      style: baseStyle(skinRef.current),
      center: [-108.822, 25.757], // Juan José Ríos, Sinaloa
      zoom: window.innerWidth < 700 ? 12.3 : 13,
      minZoom: 9,
      maxZoom: 17.5,
      maxBounds: [[-109.7, 25.05], [-108.05, 26.35]],
      attributionControl: false,
      dragRotate: false,
      pitchWithRotate: false,
      fadeDuration: 200,
    })
    mapRef.current = map
    if (import.meta.env.DEV) (window as unknown as { __map: MLMap }).__map = map
    map.touchZoomRotate.disableRotation()
    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right')

    map.on('load', () => {
      map.addSource('agebs', { type: 'geojson', data: data.agebs, promoteId: 'cvegeo' })
      map.addSource('realms', { type: 'geojson', data: data.realms })

      const before = 'water' // AGEB fills sit under water so the dam reads as a lake
      map.addLayer({ id: 'fill-realm', type: 'fill', source: 'agebs', paint: { 'fill-color': ['get', 'color'], 'fill-opacity': opacityExpr('realm', 1) } }, before)
      map.addLayer({ id: 'fill-people', type: 'fill', source: 'agebs', paint: { 'fill-color': peopleColorExpr(data.stats) as never, 'fill-opacity': 0 } }, before)
      map.addLayer({ id: 'fill-wealth', type: 'fill', source: 'agebs', paint: { 'fill-color': wealthColorExpr(wealthPrimary) as never, 'fill-opacity': 0 } }, before)
      map.addLayer({ id: 'fill-wildlife', type: 'fill', source: 'agebs', paint: { 'fill-color': wildlifeColorExpr(data.stats) as never, 'fill-opacity': 0 } }, before)
      map.addLayer({ id: 'fill-green', type: 'fill', source: 'agebs', paint: { 'fill-color': greenColorExpr(data.stats) as never, 'fill-opacity': 0 } }, before)
      map.addLayer({ id: 'fill-work', type: 'fill', source: 'agebs', paint: { 'fill-color': workColorExpr(data.stats) as never, 'fill-opacity': 0 } }, before)
      map.addLayer({ id: 'fill-water', type: 'fill', source: 'agebs', paint: { 'fill-color': waterColorExpr(data.stats) as never, 'fill-opacity': 0 } }, before)
      map.addLayer({ id: 'fill-campo', type: 'fill', source: 'agebs', paint: { 'fill-color': campoColorExpr() as never, 'fill-opacity': 0 } }, before)
      map.addLayer({ id: 'fill-heat', type: 'fill', source: 'agebs', paint: { 'fill-color': heatColorExpr(data.stats) as never, 'fill-opacity': 0 } }, before)
      // satellite heat picture: shown close-up in Calor mode, under the barrio borders
      const img = data.stats.heat?.image
      if (img) {
        const [w, s, e, n] = img.bounds
        map.addSource('heat-img', { type: 'image', url: dataUrl(img.file), coordinates: [[w, n], [e, n], [e, s], [w, s]] })
        map.addLayer({ id: 'heat-img', type: 'raster', source: 'heat-img', paint: { 'raster-opacity': 0, 'raster-fade-duration': 0, 'raster-resampling': 'linear' } }, before)
      }
      // shimmering heat waves over the hottest barrios
      for (const hot of data.stats.heat?.hottest ?? []) {
        const f = data.agebs.features.find(x => (x.properties as Ageb).cvegeo === hot.cvegeo)
        if (!f) continue
        const g = f.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon
        const ring = (g.type === 'Polygon' ? g.coordinates[0] : g.coordinates[0][0]) as [number, number][]
        const c: [number, number] = [ring.reduce((t, p) => t + p[0], 0) / ring.length, ring.reduce((t, p) => t + p[1], 0) / ring.length]
        const div = document.createElement('div')
        div.className = 'heat-wave hidden'
        div.title = `${Math.round(hot.lst)} °C en el suelo`
        div.innerHTML = `<svg viewBox="0 0 40 30" width="40" height="30" aria-hidden="true">${[8, 20, 32].map((x, i) =>
          `<path d="M${x} 28c-4-4 4-7 0-11s4-7 0-11" fill="none" stroke="#b03426" stroke-width="2.6" stroke-linecap="round" style="animation-delay:${-i * 0.4}s"/>`).join('')}</svg><span>${Math.round(hot.lst)} °C</span>`
        heatMarkers.current.push(new maplibregl.Marker({ element: div, anchor: 'bottom' }).setLngLat(c).addTo(map))
      }
      // AGEBs created after the census: diagonal hatching instead of a colour
      map.addLayer({
        id: 'no-census', type: 'line', source: 'agebs', filter: ['==', ['get', 'in_census'], false],
        paint: { 'line-color': INK, 'line-width': 1, 'line-dasharray': [1, 2], 'line-opacity': 0.7 },
      })

      // roads (INEGI vialidades), drawn as ink strokes
      map.addLayer({
        id: 'roads-casing', type: 'line', source: 'roads', minzoom: 10.5,
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: {
          'line-color': INK, 'line-opacity': ['interpolate', ['linear'], ['zoom'], 10.5, 0, 12, 0.5],
          'line-width': ['interpolate', ['linear'], ['zoom'], 11, ['match', ['get', 'r'], 1, 1.6, 0.6], 16, ['match', ['get', 'r'], 1, 7, 4.5]],
        },
      })
      map.addLayer({
        id: 'roads', type: 'line', source: 'roads', minzoom: 12,
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: {
          'line-color': PALETTES[skinRef.current].road, 'line-opacity': ['interpolate', ['linear'], ['zoom'], 12, 0, 13, 0.9],
          'line-width': ['interpolate', ['linear'], ['zoom'], 12, ['match', ['get', 'r'], 1, 0.8, 0.3], 16, ['match', ['get', 'r'], 1, 4.5, 2.6]],
        },
      })

      // AGEB "county" borders appear as you zoom in
      map.addLayer({
        id: 'ageb-line', type: 'line', source: 'agebs',
        paint: {
          'line-color': INK,
          'line-opacity': ['interpolate', ['linear'], ['zoom'], 11.6, 0, 12.6, 0.45, 15, 0.25],
          'line-width': ['interpolate', ['linear'], ['zoom'], 11, 0.4, 15, 1.2],
          'line-dasharray': [3, 2],
        },
      })
      // realm borders: dark ink with an inner tinted glow (CK3-like)
      map.addLayer({
        id: 'realm-glow', type: 'line', source: 'realms',
        paint: {
          'line-color': ['get', 'color'], 'line-offset': ['interpolate', ['linear'], ['zoom'], 9, 2, 14, 5],
          'line-width': ['interpolate', ['linear'], ['zoom'], 9, 3, 14, 7], 'line-opacity': 0.55, 'line-blur': 2,
        },
      })
      map.addLayer({
        id: 'realm-line', type: 'line', source: 'realms', layout: { 'line-join': 'round' },
        paint: { 'line-color': INK, 'line-width': ['interpolate', ['linear'], ['zoom'], 9, 1.6, 14, 3.2], 'line-opacity': 0.9 },
      })
      map.addLayer({
        id: 'hover-line', type: 'line', source: 'agebs',
        paint: { 'line-color': PALETTES[skinRef.current].hover, 'line-width': 3, 'line-opacity': ['case', ['boolean', ['feature-state', 'hover'], false], 0.95, 0] },
      })
      map.addLayer({
        id: 'sel-line', type: 'line', source: 'agebs', filter: ['==', ['get', 'cvegeo'], ''],
        paint: { 'line-color': PALETTES[skinRef.current].sel, 'line-width': 4 },
      })
      map.addLayer({
        id: 'sel-line-ink', type: 'line', source: 'agebs', filter: ['==', ['get', 'cvegeo'], ''],
        paint: { 'line-color': INK, 'line-width': 1.2 },
      })

      // realm banners
      for (const r of realmsById.values()) {
        const div = document.createElement('div')
        div.className = 'banner'
        div.style.setProperty('--realm', r.color)
        div.innerHTML = `<span class="banner-art"></span><div class="banner-name"></div><div class="banner-title"></div>`
        div.addEventListener('click', e => {
          e.stopPropagation()
          const ag = data.agebs.features.filter(f => (f.properties as Ageb).realm === r.id)
          const b = new maplibregl.LngLatBounds()
          for (const f of ag) {
            const g = f.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon
            const polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates
            for (const p of polys) for (const c of p[0]) b.extend(c as [number, number])
          }
          map.fitBounds(b, { padding: 60, duration: 1400, maxZoom: 14 })
        })
        const m = new maplibregl.Marker({ element: div, anchor: 'bottom' }).setLngLat(r.label).addTo(map)
        banners.current.push({ m, r })
      }
      // banner art and text are drawn by applySkin() below

      // landmark tokens (OSM)
      fetch(dataUrl('landmarks.geojson'))
        .then(r => (r.ok ? r.json() : null))
        .then((fc: GeoJSON.FeatureCollection | null) => {
          if (!fc) return
          for (const f of fc.features) {
            const p = f.properties as { kind: string; name: string }
            const div = document.createElement('div')
            div.className = `token token-${p.kind}`
            div.dataset.minzoom = String(tokenMinZoom(p.kind, p.name))
            div.title = p.name
            div.innerHTML = `${tokenSVG(p.kind)}<span class="token-name">${escapeHtml(p.name)}</span>`
            new maplibregl.Marker({ element: div, anchor: 'bottom' })
              .setLngLat((f.geometry as GeoJSON.Point).coordinates as [number, number]).addTo(map)
          }
          updateZoomClasses()
        })

      // open on the whole city (realm view), leaving room for the HUD and mode bar
      const city = new maplibregl.LngLatBounds()
      for (const f of data.realms.features) {
        if (!(f.properties as Realm).id.startsWith('R')) continue
        const g = f.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon
        for (const poly of g.type === 'Polygon' ? [g.coordinates] : g.coordinates) for (const c of poly[0]) city.extend(c as [number, number])
      }
      const wide = window.innerWidth > 900
      map.fitBounds(city, { padding: { top: 70, bottom: 110, left: wide ? 60 : 10, right: wide ? 60 : 10 }, duration: 0 })

      updateZoomClasses()
      applyWeights()
      applySkin() // in case the skin changed while the map was loading
      if (modeRef.current === 'wildlife') loadWildlife()
      if (modeRef.current === 'green') loadTrees()
      if (modeRef.current === 'work') loadWork()
      if (modeRef.current === 'water') loadWater()
      if (modeRef.current === 'campo') loadCampo()
    })

    // lazy layers for the "block" tier
    let lazyLoaded = false
    function loadLazy() {
      if (lazyLoaded || map.getZoom() < 13.4) return
      lazyLoaded = true
      map.addSource('roads-minor', { type: 'geojson', data: dataUrl('roads_minor.geojson') })
      map.addSource('blocks', { type: 'geojson', data: dataUrl(data.dir + 'blocks.geojson') })
      map.addLayer({
        id: 'blocks-people', type: 'fill', source: 'blocks', minzoom: 13.8,
        paint: { 'fill-color': blockPeopleColorExpr(data.stats) as never, 'fill-opacity': 0 },
      }, 'roads-casing')
      map.addLayer({
        id: 'blocks-line', type: 'line', source: 'blocks', minzoom: 14,
        paint: { 'line-color': PALETTES[skinRef.current].ink, 'line-opacity': ['interpolate', ['linear'], ['zoom'], 14, 0, 15, 0.35], 'line-width': 0.6 },
      }, 'roads-casing')
      map.addLayer({
        id: 'roads-minor', type: 'line', source: 'roads-minor', minzoom: 14,
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': PALETTES[skinRef.current].road, 'line-opacity': ['interpolate', ['linear'], ['zoom'], 14, 0, 15, 0.8], 'line-width': ['interpolate', ['linear'], ['zoom'], 14, 0.5, 17, 3] },
      }, 'roads-casing')
      applyWeights()
    }

    mapFns.current.loadWildlife = loadWildlife
    mapFns.current.loadTrees = loadTrees
    mapFns.current.loadWork = loadWork
    mapFns.current.loadWater = loadWater
    mapFns.current.loadCampo = loadCampo
    // Campo: INEGI farmland polygons + the WorldCover cropland picture, fetched the first time Campo is opened.
    // The farms are outside the town, so the first opening also zooms out to show them.
    let campoState: 'none' | 'loading' | 'ready' = 'none'
    async function loadCampo() {
      const cs = data.stats.campo
      if (campoState !== 'none' || !map.getLayer('fill-realm') || !cs || (!cs.usv && !cs.cropland)) return
      campoState = 'loading'
      const fc: GeoJSON.FeatureCollection | null = cs.usv
        ? await fetch(dataUrl('campo.geojson')).then(r => (r.ok ? r.json() : null)).catch(() => null)
        : null
      if (mapRef.current !== map) return
      const under = 'fill-realm' // below every barrio fill: the town stays on top of the fields
      if (fc) {
        if (!map.hasImage('hatch')) map.addImage('hatch', hatchImage(), { pixelRatio: 2 })
        map.addSource('campo', { type: 'geojson', data: fc })
        const color = ['match', ['get', 'tipo'], ...Object.entries(CAMPO_KIND).flatMap(([k, v]) => [k, v.color]), '#e6dcaa']
        map.addLayer({ id: 'campo-fill', type: 'fill', source: 'campo', paint: { 'fill-color': color as never, 'fill-opacity': 0 } }, under)
        map.addLayer({
          id: 'campo-hatch', type: 'fill', source: 'campo',
          filter: ['in', ['get', 'tipo'], ['literal', Object.keys(CAMPO_KIND).filter(k => CAMPO_KIND[k].hatch)]],
          paint: { 'fill-pattern': 'hatch', 'fill-opacity': 0 },
        }, under)
        map.addLayer({
          id: 'campo-line', type: 'line', source: 'campo',
          paint: { 'line-color': PALETTES[skinRef.current].ink, 'line-width': ['interpolate', ['linear'], ['zoom'], 9, 0.4, 14, 1.2] as never, 'line-opacity': 0 },
        }, under)
      }
      const img = cs.cropland?.image
      if (img) {
        const [w, s, e, n] = img.bounds
        map.addSource('campo-img', { type: 'image', url: dataUrl(img.file), coordinates: [[w, n], [e, n], [e, s], [w, s]] })
        map.addLayer({ id: 'campo-img', type: 'raster', source: 'campo-img', paint: { 'raster-opacity': 0, 'raster-fade-duration': 0, 'raster-resampling': 'nearest' } }, under)
      }
      campoState = 'ready'
      applyWeights()
      if (modeRef.current === 'campo' && map.getZoom() > 11.4) {
        const b = new maplibregl.LngLatBounds()
        for (const f of fc?.features ?? []) {
          const g = f.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon
          for (const poly of g.type === 'Polygon' ? [g.coordinates] : g.coordinates) for (const c of poly[0]) b.extend(c as [number, number])
        }
        if (b.isEmpty() && img) b.extend([img.bounds[0], img.bounds[1]]).extend([img.bounds[2], img.bounds[3]])
        if (!b.isEmpty()) map.fitBounds(b, { padding: { top: 70, bottom: 130, left: 20, right: 20 }, duration: 1400, maxZoom: 11 })
      }
    }
    // REPDA wells and intakes are fetched the first time Agua is opened (compact rows → GeoJSON here)
    let waterState: 'none' | 'loading' | 'ready' = 'none'
    async function loadWater() {
      if (waterState !== 'none' || !map.getLayer('fill-realm') || !data.stats.water?.rights) return
      waterState = 'loading'
      const r = await fetch(dataUrl('water.json')).catch(() => null)
      const raw: { uses: WaterUse[]; aquifers: string[]; rows: [number, number, 0 | 1, number, number, number, string, string, 0 | 1][] } | null =
        r && r.ok ? await r.json().catch(() => null) : null
      if (!raw || mapRef.current !== map) {
        waterState = 'none'
        return
      }
      await addWaterImages(map)
      const fc: GeoJSON.FeatureCollection = {
        type: 'FeatureCollection',
        features: raw.rows.map(([lon, lat, k, u, v, aq, h, y, d]) => ({
          type: 'Feature', geometry: { type: 'Point', coordinates: [lon, lat] },
          properties: { k, u: raw.uses[u], v, aq: aq >= 0 ? raw.aquifers[aq] : null, h, y, d },
        })),
      }
      map.addSource('water-pts', { type: 'geojson', data: fc })
      // size grows with the yearly volume; 1 million m³ or more shows from far away
      const size = (k: number) => ['*', k, ['interpolate', ['linear'], ['ln', ['max', ['get', 'v'], 1000]], 6.9, 0.55, 13.8, 1, 18.4, 1.6]]
      for (const [id, min, f] of [['water-big', 9, ['>=', ['get', 'v'], 1e6]], ['water-small', 12, ['<', ['get', 'v'], 1e6]]] as const) {
        map.addLayer({
          id, type: 'symbol', source: 'water-pts', minzoom: min, filter: f as never,
          layout: {
            'icon-image': ['concat', 'a-', ['get', 'u'], '-', ['to-string', ['get', 'k']]],
            'icon-size': ['interpolate', ['linear'], ['zoom'], 9, size(0.22), 12, size(0.34), 15, size(0.6), 17, size(0.8)] as never,
            'icon-allow-overlap': ['step', ['zoom'], false, 15, true],
            'icon-padding': 0,
            'symbol-sort-key': ['-', 0, ['get', 'v']],
            visibility: 'none',
          },
          paint: { 'icon-opacity': ['interpolate', ['linear'], ['zoom'], min, 0, min + 0.6, 1] },
        })
      }
      waterState = 'ready'
      showWater()
    }
    // DENUE businesses are fetched the first time Chamba is opened (compact rows → GeoJSON here)
    let workState: 'none' | 'loading' | 'ready' = 'none'
    async function loadWork() {
      if (workState !== 'none' || !map.getLayer('fill-realm') || !data.stats.work) return
      workState = 'loading'
      const r = await fetch(dataUrl('work.json')).catch(() => null)
      const raw: { groups: WorkGroup[]; rows: [number, number, number, number, string, string, string][]; acts: Record<string, string> } | null =
        r && r.ok ? await r.json().catch(() => null) : null
      if (!raw || mapRef.current !== map) {
        workState = 'none'
        return
      }
      bizActs.current = raw.acts
      await addWorkImages(map)
      const fc: GeoJSON.FeatureCollection = {
        type: 'FeatureCollection',
        features: raw.rows.map(([lon, lat, g, s, n, c, a]) => ({
          type: 'Feature', geometry: { type: 'Point', coordinates: [lon, lat] },
          properties: { g: raw.groups[g], s, n, c, a },
        })),
      }
      map.addSource('work', { type: 'geojson', data: fc })
      // big employers (101+ people) show from the city view; everything else once you are close
      const size = (k: number) => ['*', k, ['+', 0.6, ['*', 0.1, ['get', 's']]]]
      for (const [id, min, f] of [['work-big', 10.5, ['>=', ['get', 's'], 5]], ['work-pts', 14, ['<', ['get', 's'], 5]]] as const) {
        map.addLayer({
          id, type: 'symbol', source: 'work', minzoom: min, filter: f as never,
          layout: {
            'icon-image': ['concat', 'j-', ['get', 'g']],
            'icon-size': ['interpolate', ['linear'], ['zoom'], 10.5, size(0.26), 14, size(0.42), 17, size(0.8)] as never,
            'icon-allow-overlap': ['step', ['zoom'], false, 16, true],
            'icon-padding': 0,
            'symbol-sort-key': ['-', 0, ['get', 's']],
            visibility: 'none',
          },
          paint: { 'icon-opacity': ['interpolate', ['linear'], ['zoom'], min, 0, min + 0.6, 1] },
        })
      }
      workState = 'ready'
      showWork()
    }
    // cartoon trees are fetched the first time Verde is opened
    let treesState: 'none' | 'loading' | 'ready' = 'none'
    async function loadTrees() {
      if (treesState !== 'none' || !map.getLayer('fill-realm') || !data.stats.green) return
      treesState = 'loading'
      await addTreeImage(map)
      if (mapRef.current !== map) return
      map.addSource('trees', { type: 'geojson', data: dataUrl('trees.geojson') })
      // size: grows with zoom, and with how green that spot is today (NDVI)
      const f = ['interpolate', ['linear'], ['coalesce', ['get', 'v'], 0.2], 0.05, 0.6, 0.25, 1, 0.5, 1.5]
      map.addLayer({
        id: 'trees', type: 'symbol', source: 'trees', minzoom: 11.5,
        layout: {
          'icon-image': 'tree', 'icon-allow-overlap': ['step', ['zoom'], false, 15, true], 'icon-padding': 0,
          'icon-size': ['interpolate', ['linear'], ['zoom'], 11.5, ['*', 0.16, f], 14, ['*', 0.32, f], 17, ['*', 0.7, f]] as never,
          'symbol-sort-key': ['-', 0, ['coalesce', ['get', 'v'], 0]],
          visibility: modeRef.current === 'green' ? 'visible' : 'none',
        },
        paint: { 'icon-opacity': ['interpolate', ['linear'], ['zoom'], 11.5, 0, 12.2, 1] },
      })
      treesState = 'ready'
    }
    // Fauna layer is fetched only the first time the mode is opened
    async function loadWildlife() {
      if (wildState.current !== 'none' || !map.getLayer('fill-realm')) return
      wildState.current = 'loading'
      const r = await fetch(dataUrl('wildlife.geojson')).catch(() => null)
      const fc: GeoJSON.FeatureCollection | null = r && r.ok ? await r.json().catch(() => null) : null
      if (!fc || mapRef.current !== map) {
        wildState.current = 'none'
        return
      }
      await addCritterImages(map)
      map.addSource('wildlife', { type: 'geojson', data: fc })
      map.addLayer({
        id: 'critters', type: 'symbol', source: 'wildlife',
        layout: {
          'icon-image': ['concat', 'c-', ['get', 'g']],
          'icon-size': ['interpolate', ['linear'], ['zoom'], 10, 0.3, 13, 0.45, 16, 0.7],
          'icon-allow-overlap': ['step', ['zoom'], false, 15.5, true],
          'icon-padding': 0,
          'symbol-sort-key': ['-', 0, ['get', 'w']],
          visibility: 'none',
        },
      })
      // this week's new sightings get a live, animated marker
      for (const f of fc.features) {
        const p = f.properties as Sighting
        if (!p.w) continue
        const div = document.createElement('div')
        div.className = `critter-live critter-${p.g}`
        div.innerHTML = `${critterSVG(p.g, 40)}<span class="critter-new">¡Nuevo!</span>`
        div.addEventListener('mouseenter', () => {
          const pt = map.project((f.geometry as GeoJSON.Point).coordinates as [number, number])
          cb.current.onSighting({ x: pt.x, y: pt.y, s: p, pinned: false })
        })
        div.addEventListener('mouseleave', () => cb.current.onSighting(null))
        div.addEventListener('click', e => {
          e.stopPropagation()
          const pt = map.project((f.geometry as GeoJSON.Point).coordinates as [number, number])
          cb.current.onSighting({ x: pt.x, y: pt.y, s: p, pinned: true })
        })
        const m = new maplibregl.Marker({ element: div, anchor: 'bottom' })
          .setLngLat((f.geometry as GeoJSON.Point).coordinates as [number, number]).addTo(map)
        liveMarkers.current.push({ m, g: p.g })
      }
      wildState.current = 'ready'
      showWildlife()
    }

    function updateZoomClasses() {
      const z = map.getZoom()
      const container = el.current!
      container.dataset.tier = tierOf(z)
      container.style.setProperty('--z', String(z))
      container.querySelectorAll<HTMLElement>('.token').forEach(t => {
        t.classList.toggle('hidden', z < Number(t.dataset.minzoom))
      })
      cb.current.onTier(tierOf(z))
      declutterBanners()
    }
    // hide banners that would overlap a more populous realm's banner
    function declutterBanners() {
      const placed: { x: number; y: number; w: number }[] = []
      const sorted = [...banners.current].sort((a, b) => b.r.pop - a.r.pop)
      for (const { m, r } of sorted) {
        const p = map.project(r.label)
        const sk = skinRef.current
        const w = Math.min(170, 30 + realmLabel(r, sk).name.length * 7.5)
        const hit = placed.some(q => Math.abs(q.x - p.x) < (q.w + w) / 2 && Math.abs(q.y - p.y) < (sk === 'atlas' ? 76 : sk === 'sencillo' ? 30 : 62))
        m.getElement().classList.toggle('collide', hit)
        if (!hit) placed.push({ x: p.x, y: p.y, w })
      }
    }
    map.on('zoom', updateZoomClasses)
    map.on('moveend', declutterBanners)
    map.on('zoomend', loadLazy)

    // ---------- interaction ----------
    let hoverId: string | null = null
    const setHover = (id: string | null) => {
      if (hoverId === id) return
      if (hoverId) map.setFeatureState({ source: 'agebs', id: hoverId }, { hover: false })
      hoverId = id
      if (id) map.setFeatureState({ source: 'agebs', id }, { hover: true })
    }
    const pick = (pt: maplibregl.PointLike): MapGeoJSONFeature | undefined =>
      !map.getLayer('fill-realm') ? undefined : map.queryRenderedFeatures(pt, { layers: FILL_MODES.map(m => `fill-${m}`) })[0]
    const pickCritter = (pt: maplibregl.Point): Pick<SightingInfo, 's' | 'b' | 'well' | 'field'> | undefined => {
      const box: [maplibregl.PointLike, maplibregl.PointLike] = [[pt.x - 8, pt.y - 8], [pt.x + 8, pt.y + 8]]
      if (modeRef.current === 'campo' && map.getLayer('campo-fill')) {
        // a barrio under the pointer wins: the fields card is for the farmland around the town
        if (pick(pt)) return undefined
        const p = map.queryRenderedFeatures(pt, { layers: ['campo-fill'] })[0]?.properties as Field | undefined
        return p ? { field: p } : undefined
      }
      if (modeRef.current === 'water' && map.getLayer('water-small')) {
        const p = map.queryRenderedFeatures(box, { layers: ['water-big', 'water-small'] })[0]?.properties as Well | undefined
        return p ? { well: { ...p, aq: (p.aq as unknown) === 'null' ? null : p.aq } } : undefined
      }
      if (modeRef.current === 'work' && map.getLayer('work-pts')) {
        const p = map.queryRenderedFeatures(box, { layers: ['work-big', 'work-pts'] })[0]?.properties as Biz | undefined
        return p ? { b: { ...p, act: bizActs.current[p.c] } } : undefined
      }
      if (modeRef.current !== 'wildlife' || !map.getLayer('critters')) return undefined
      const s = map.queryRenderedFeatures(box, { layers: ['critters'] })[0]?.properties as Sighting | undefined
      return s ? { s } : undefined
    }

    map.on('mousemove', e => {
      const c = pickCritter(e.point)
      if (c) {
        setHover(null)
        cb.current.onHover(null)
        map.getCanvas().style.cursor = 'pointer'
        cb.current.onSighting({ x: e.point.x, y: e.point.y, ...c, pinned: false })
        return
      }
      cb.current.onSighting(null)
      const f = pick(e.point)
      if (!f) {
        setHover(null)
        map.getCanvas().style.cursor = ''
        cb.current.onHover(null)
        return
      }
      const a = f.properties as unknown as Ageb
      setHover(a.cvegeo)
      map.getCanvas().style.cursor = 'pointer'
      const realm = realmsById.get(a.realm)!
      cb.current.onHover({ x: e.point.x, y: e.point.y, ageb: a, realm })
    })
    map.on('mouseout', () => {
      setHover(null)
      cb.current.onHover(null)
    })
    map.on('click', e => {
      const c = pickCritter(e.point)
      if (c) return cb.current.onSighting({ x: e.point.x, y: e.point.y, ...c, pinned: true })
      cb.current.onSighting(null, true)
      const f = pick(e.point)
      if (!f) return cb.current.onSelect(null)
      const a = f.properties as unknown as Ageb
      if (tierOf(map.getZoom()) === 'realm') {
        // CK3-like: clicking a realm from afar zooms toward it first
        map.flyTo({ center: e.lngLat, zoom: 13.4, duration: 1200 })
      }
      cb.current.onSelect(a.cvegeo)
    })

    return () => {
      cancelAnimationFrame(anim.current)
      map.remove()
      mapRef.current = null
      banners.current = []
      liveMarkers.current = []
      heatMarkers.current = []
      wildState.current = 'none'
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])

  // ---------- fauna visibility & group filter ----------
  const mapFns = useRef<{ loadWildlife?: () => void; loadTrees?: () => void; loadWork?: () => void; loadWater?: () => void; loadCampo?: () => void }>({})
  const bizActs = useRef<Record<string, string>>({})
  function showWork() {
    const map = mapRef.current
    if (!map?.getLayer('work-pts')) return
    const gs = [...workGroupsRef.current]
    for (const [id, f] of [['work-big', ['>=', ['get', 's'], 5]], ['work-pts', ['<', ['get', 's'], 5]]] as const) {
      map.setLayoutProperty(id, 'visibility', modeRef.current === 'work' ? 'visible' : 'none')
      map.setFilter(id, ['all', f, ['in', ['get', 'g'], ['literal', gs.length ? gs : WORK_GROUPS]]] as never)
    }
  }
  useEffect(() => {
    if (mode === 'work') mapFns.current.loadWork?.()
    showWork()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, workGroups])
  function showWater() {
    const map = mapRef.current
    if (!map?.getLayer('water-small')) return
    const us = [...waterUsesRef.current]
    for (const [id, f] of [['water-big', ['>=', ['get', 'v'], 1e6]], ['water-small', ['<', ['get', 'v'], 1e6]]] as const) {
      map.setLayoutProperty(id, 'visibility', modeRef.current === 'water' ? 'visible' : 'none')
      map.setFilter(id, ['all', f, ['in', ['get', 'u'], ['literal', us.length ? us : WATER_USES]]] as never)
    }
  }
  useEffect(() => {
    if (mode === 'campo') mapFns.current.loadCampo?.()
  }, [mode])
  useEffect(() => {
    if (mode === 'water') mapFns.current.loadWater?.()
    showWater()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, waterUses])
  function showWildlife() {
    const map = mapRef.current
    if (!map?.getLayer('critters')) return
    const on = modeRef.current === 'wildlife'
    const gs = [...groupsRef.current]
    map.setLayoutProperty('critters', 'visibility', on ? 'visible' : 'none')
    map.setFilter('critters', ['in', ['get', 'g'], ['literal', gs]] as never)
    for (const { m, g } of liveMarkers.current) m.getElement().classList.toggle('hidden', !on || !groupsRef.current.has(g))
  }
  useEffect(() => {
    for (const m of heatMarkers.current) m.getElement().classList.toggle('hidden', mode !== 'heat')
    if (mode === 'green') mapFns.current.loadTrees?.()
    const map = mapRef.current
    if (map?.getLayer('trees')) map.setLayoutProperty('trees', 'visibility', mode === 'green' ? 'visible' : 'none')
  }, [mode])
  useEffect(() => {
    if (mode === 'wildlife') mapFns.current.loadWildlife?.()
    showWildlife()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, groups])

  // ---------- mode crossfade ----------
  function applyWeights() {
    const map = mapRef.current
    if (!map || !map.getLayer('fill-realm')) return
    const w = weights.current
    for (const m of FILL_MODES) map.setPaintProperty(`fill-${m}`, 'fill-opacity', opacityExpr(m, w[m]))
    if (map.getLayer('heat-img')) {
      map.setPaintProperty('heat-img', 'raster-opacity', ['interpolate', ['linear'], ['zoom'], 11.8, 0, 13, 0.8 * w.heat] as never)
      map.setPaintProperty('fill-heat', 'fill-opacity', ['interpolate', ['linear'], ['zoom'], 9, 0.88 * w.heat, 12, 0.8 * w.heat, 13, 0.08 * w.heat] as never)
    }
    if (map.getLayer('campo-fill')) {
      map.setPaintProperty('campo-fill', 'fill-opacity', 0.55 * w.campo)
      map.setPaintProperty('campo-hatch', 'fill-opacity', 0.8 * w.campo)
      map.setPaintProperty('campo-line', 'line-opacity', 0.45 * w.campo)
    }
    if (map.getLayer('campo-img')) map.setPaintProperty('campo-img', 'raster-opacity', 0.75 * w.campo)
    if (map.getLayer('blocks-people')) {
      map.setPaintProperty('blocks-people', 'fill-opacity', ['interpolate', ['linear'], ['zoom'], 13.8, 0, 14.6, 0.85 * w.people] as never)
      map.setPaintProperty('fill-people', 'fill-opacity', ['interpolate', ['linear'], ['zoom'], 9, 0.88 * w.people, 12, 0.82 * w.people, 13.8, 0.7 * w.people, 14.6, 0.12 * w.people] as never)
    }
  }

  useEffect(() => {
    const target: Record<string, number> = { realm: 0, people: 0, wealth: 0, wildlife: 0, heat: 0, green: 0, work: 0, water: 0, campo: 0 }
    // modes without a fill of their own (not built yet) keep the realm map underneath, dimmed
    if (FILL_MODES.includes(mode)) target[mode] = 1
    else target.realm = 0.35
    const start = { ...weights.current }
    const t0 = performance.now()
    const D = 650
    cancelAnimationFrame(anim.current)
    const step = (t: number) => {
      const k = Math.min(1, (t - t0) / D)
      const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2
      for (const m of FILL_MODES) weights.current[m] = start[m] + (target[m] - start[m]) * e
      applyWeights()
      if (k < 1) anim.current = requestAnimationFrame(step)
    }
    anim.current = requestAnimationFrame(step)
    if (el.current) el.current.dataset.mode = mode
  }, [mode])

  useEffect(() => {
    const map = mapRef.current
    if (map?.getLayer('fill-wealth')) map.setPaintProperty('fill-wealth', 'fill-color', wealthColorExpr(wealthPrimary) as never)
  }, [wealthPrimary])

  useEffect(() => {
    const map = mapRef.current
    if (!map?.getLayer('sel-line')) return
    const f = ['==', ['get', 'cvegeo'], selected ?? ''] as never
    map.setFilter('sel-line', f)
    map.setFilter('sel-line-ink', f)
  }, [selected])

  function renderBannerText() {
    const s = skinRef.current
    for (const { m, r } of banners.current) {
      const e = m.getElement()
      const L = realmLabel(r, s)
      e.querySelector('.banner-art')!.innerHTML = realmBannerSVG(s, r.color, r.charge, s === 'atlas' ? 44 : 32)
      e.querySelector('.banner-name')!.textContent = L.name
      e.querySelector('.banner-title')!.textContent = L.sub
      e.setAttribute('aria-label', `${L.name} ${L.sub}`)
    }
  }

  // ---------- skin: repaint the base map and lines, redraw banners (no setStyle, so our layers stay) ----------
  function applySkin() {
    const map = mapRef.current
    if (!map || !map.getLayer('fill-realm')) return
    const P = PALETTES[skinRef.current]
    for (const [id, prop, k] of SKIN_PAINT) if (map.getLayer(id)) map.setPaintProperty(id, prop, P[k])
    renderBannerText()
    map.fire('moveend') // re-run banner declutter: sizes differ per skin
  }
  useEffect(() => {
    applySkin()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [skin])

  return <div ref={el} className="map" data-mode={mode} />
}

/** 16×16 diagonal hatching (drawn at 2×) for rain-fed farmland: told apart by texture, not only colour. */
function hatchImage(): ImageData {
  const n = 16
  const d = new Uint8ClampedArray(n * n * 4)
  for (let y = 0; y < n; y++)
    for (let x = 0; x < n; x++) {
      if ((x + y) % 8 > 1) continue
      d.set([92, 84, 30, 200], (y * n + x) * 4)
    }
  return new ImageData(d, n, n)
}

function escapeHtml(s: string) {
  return s.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!)
}
