# AGENTS.md — Juan José Ríos: El Mapa Vivo (mapa-cherrios)

A stylised, strategy-game-looking map of Juan José Ríos, Sinaloa (Civilization VI / Crusader Kings III feel, Norteño
look), built only from real, open data. Static site (Vite + React + MapLibre) fed by a Python pipeline that
writes `public/data/`. A GitHub Action refreshes the data weekly and redeploys to Cloudflare.
Forked from Hermosillo: El Mapa Vivo (jmsalcido/mapa-hermosillo).

## Two views ("épocas")

Juan José Ríos was part of Guasave (and El Estero part of Ahome) until the 2021 decree created municipio
25-020. INEGI re-keyed every AGEB, so 2020 numbers cannot be joined to today's zones. The app has a switch
next to the style switch (`src/era.ts`, `?era=antes`, localStorage `jjr-era`):

- **Municipio** (default, `public/data/`): Marco Geoestadístico 2025 zones of 25-020 + every live layer
  (Fauna, Calor, Verde, Chamba, Agua, Campo). Census-based modes (Gente, Bienestar) show "solo en «Antes de ser
  Municipio»"; never fill them with re-apportioned 2020 numbers.
- **Antes de ser Municipio** (`public/data/antes/`): Marco Geoestadístico 2020 (census edition, state
  shapefile zip) for Guasave 011-0138 + Ahome 001-0136, with Censo 2020 and CONAPO / CONEVAL 2020. Only
  modes in `ANTES_MODES` (Territorio, Gente, Bienestar, and Campo with only the SIAP tables of Guasave / Ahome); live modes say "solo en «Municipio»".

## Non-negotiable rules

1. **Real data only.** Every number on screen comes from a cited source in `public/data/manifest.json`.
   If a source fails, show "Datos no disponibles" / "sin datos". Never invent, interpolate or use placeholders.
2. **Missing ≠ zero.** INEGI `*` cells (confidentiality) are `null`, a real `0` stays `0`. Keep that distinction
   through the pipeline and the UI.
3. **Modelled or estimated values are labelled** in the UI ("cálculo aproximado", "modelado", "visto desde
   satélite"). Examples: Chamba jobs (DENUE size-range midpoints), NASA POWER temperature, NDVI trees.
4. **UI language is Spanish (Mexico) only**, written in plain words for non-technical people. No English in the
   interface. Strings live in `src/i18n.ts` or inline JSX in Spanish.
5. **Skins** (`src/skin.ts`, `?skin=sencillo|norteno|atlas`, HUD switch, saved in localStorage `hlm-estilo`).
   **"Sencillo" is the default**: a plain, modern, easy-to-read look that puts the data first — white panels,
   one sans-serif (Inter), one blue accent, light-grey base map, no ornaments (no clouds/vignette, shields,
   banners or house drawing; territories are "Zonas" shown by their real place name with a colour dot), and the
   ficha marks the median barrio ("típico") next to each number from `stats.ranges` (only when the value exists).
   **Norteño western** (optional): leather, stitching, conchos, brass rivets, sarape stripe, cattle-brand (fierro)
   heraldry; fonts Rye / Zilla Slab / Alegreya. Inspired by that aesthetic; never copy any game's or artist's
   art, names, logos or likeness.
   "Atlas antiguo" (`?skin=atlas`) is an old hand-inked fantasy-atlas look (aged vellum, parchment panels inked in black and red,
   wax seals, crowned heater shields with ribbon names, compass rose, ripple lines along the sea; fonts Cinzel Decorative / IM Fell English / Uncial Antiqua). It is inspired by classic fantasy
   cartography in general: never use Tolkien's (or any book's or game's) names, languages, scripts or artwork.
   Its realm names are invented in `src/atlasNames.ts` (checked against a deny-list) and always shown with a
   Spanish gloss and the real place name. Skins change only looks and flavour words, never data or data ramps.
6. **Colour-blind-safe palettes**: single-hue ramps with monotonic lightness, or blue↔orange diverging. Point
   symbols differ by silhouette, not only colour.
7. **Privacy**: no phones, e-mails, addresses of businesses; iNaturalist obscured observations are never placed;
   only openly licensed (CC0 / CC-BY*) observations are kept and credited.
8. **Percentages must be 0–100.** Use the denominator INEGI defines for each numerator (see `DATA.md →
   Census percentages`). `people.check_ratios` aborts the run otherwise — don't weaken it.
9. **This is a free project — keep it at $0.** Before adding any service, API, dataset, font, library or
   hosting feature that needs a paid plan, a commercial licence, a credit card or a restrictive licence, look
   for a free / open alternative first (open data, open-source library, free tier). Only if none exists, stop
   and ask the owner before adding it; never sign up for or enable anything paid on your own.
   Today everything is free: public GitHub repo (unlimited Actions minutes, 10 GB cache), Cloudflare Workers
   static assets on the free plan (static requests are free and unlimited; 25 MiB per file, 20,000 files),
   open data sources (INEGI, CONAPO, CONEVAL, CONAGUA REPDA via Zenodo, SMN drought monitor, SIAP cierre agrícola, INEGI USV Serie VII via CONABIO, OSM, iNaturalist, NASA POWER, Landsat, Sentinel-2, ESA
   WorldCover via the free Microsoft Planetary Computer), AWS Terrain Tiles, Google Fonts, GTM / GA4 standard.
   Things that would break this: making the repo private (Actions minutes become limited), Worker code that
   runs on every request (counts against the free daily limit), files over 25 MiB, paid map tiles or APIs.

## Commands

```bash
npm install
npm run dev                 # Vite on http://localhost:5178 (see .claude/launch.json)
npm run build               # tsc -b && vite build → dist/
npm run data                # full pipeline (= uv run --directory pipeline python -m hlm.run)

# faster partial runs; skipped data modes KEEP last run's numbers (see run.py → _carry_over)
uv run --directory pipeline python -m hlm.run --skip blocks,streets,osm
uv run --directory pipeline python -m hlm.run --skip blocks,streets,osm,wildlife,heat,green,water,campo   # only Chamba

# deploy (Cloudflare Workers static assets, account "vinc")
npm run build && CLOUDFLARE_ACCOUNT_ID=<vinc account id> npx wrangler deploy
```

The full run builds both views (`run.py → build_antes`). Run the pipeline with `--directory pipeline` (not `--project pipeline`): the `hlm` package must be importable.
There is no test suite; verify with `npm run build`, a pipeline run, and the app in a browser.

## Layout

```
pipeline/hlm/      Python pipeline (uv project in pipeline/)
  common.py        paths, cached fetch() with retries + pipeline/manual fallback, Provenance/Manifest
  base.py          INEGI Marco Geoestadístico: AGEBs, blocks, streets
  people.py        Censo 2020 (AGEB + manzana), ratios, check_ratios()
  wealth.py        CONAPO IMU 2020, CONEVAL GRS 2020 (5 grades each)
  osm.py           Overpass: landmarks, water, parks, neighbourhood names
  coast.py         sea: Natural Earth 1:10m ocean clipped to the map area
  realms.py        "territorios": k-means grouping, Norteño titles, colours, fierros (derived, not official)
  wildlife.py      Fauna — iNaturalist
  heat.py          Calor — Landsat summer LST composite + NASA POWER daily max
  green.py         Verde — Sentinel-2 NDVI (now vs a year ago) + ESA WorldCover trees
  work.py          Chamba — INEGI DENUE businesses, estimated jobs
  water.py         Agua — CONAGUA REPDA water rights (Zenodo copy) + SMN drought monitor
  campo.py         Campo — INEGI USV Serie VII farmland + ESA WorldCover cropland + SIAP cierre agrícola
  chronicle.py     La Gaceta: weekly snapshot (history.json) + entries (chronicle.json)
  run.py           orchestration, stats.json, manifest.json
pipeline/manual/   hand-downloaded sources (trimmed CONAPO/CONEVAL CSVs are committed)
public/data/       pipeline output served by the site (committed)
src/
  App.tsx          state: mode, selection, groups, cards; keyboard 1–9 / Esc
  data.ts          types for every data file + loadCore()
  modes.ts         mode list, colour ramps and MapLibre colour expressions
  i18n.ts          Spanish strings and number/date formatting (es-MX)
  describe.ts      plain-language one-line description of a barrio
  analytics.ts     dataLayer events for Google Tag Manager
  skin.ts          skin state (sencillo | norteno | atlas): ?skin=, localStorage, <html data-skin>
  era.ts           view state (municipio | antes): ?era=, localStorage jjr-era, ANTES_MODES
  atlasNames.ts    invented realm names + Spanish glosses for the Atlas skin
  map/             MapView (layers, lazy loading, crossfade, interaction), base style
  art/             SVG art: heraldry, landmark tokens, critters, trees, business icons, portrait
  ui/              Ledger (HUD), ModeBar, Legend, Tooltip, ProvincePanel (ficha), Chronicle, cards, Welcome
```

## Adding or changing a map mode

Follow the existing pattern (Fauna / Calor / Verde / Chamba are good templates):

1. `pipeline/hlm/<mode>.py`: fetch via `fetch()` (cache + manual fallback), register a `Provenance`, set
   `manifest.layer(<mode>, "ok" | "unavailable", [...])`, add per-AGEB fields with a short prefix, return
   a stats dict. On failure: mark unavailable, return `{}` — never raise past `run.py` for a data outage.
2. `run.py`: call it, add breaks to `stats["breaks"]`, add the section to `stats`, add the field rules to
   `CARRY` so `--skip` keeps old numbers.
3. `chronicle.py`: Gaceta entries only from measured numbers, each with a `source`; kinds share a family
   prefix (`work`, `work_new`, …) so partial runs replace only their own entries.
4. Frontend: types in `data.ts`, ramp + expression in `modes.ts`, fill layer + lazy point layer in
   `MapView.tsx` (fetch on first open of the mode), legend (plain words + source + year), tooltip, ficha
   section, credits.
5. Document the dataset and its rules in `DATA.md`; update `pipeline/README.md`.

## Gotchas learned the hard way

- **Census dwelling denominators**: `VPH_*` include dwellings without occupant info → divide by `VIVPARH_CV`,
  not `VIVPAR_HAB` (that produced 540 %). Empty homes use `TVIVPAR`.
- **CONEVAL GRS has five grades**, not three.
- **CONAPO / CONEVAL portals return 403 to scripts.** Don't try to bypass it; use `pipeline/manual/`.
- **CONAGUA sites (datos.conagua, SINA, REPDA, SIGA) sit behind an Incapsula bot wall.** Don't bypass it: REPDA
  comes from the Zenodo copy of CONAGUA's releases; dam levels are not available to scripts.
- **SMN drought table: an empty cell means "sin sequía"**, not missing data.
- **Mode bar on phones**: 9 modes don't fit 375 px, so under 760 px the belt scrolls sideways (fixed 46 px buttons,
  `ModeBar` scrolls the active one into view). Check a new mode's label at 8.5–10 px in all three skins.
- **Planetary Computer SAS tokens** are per collection: `/api/sas/v1/token/landsat-c2-l2`, `sentinel-2-l2a`,
  `esa-worldcover`.
- **Standalone SVGs must be valid XML** (e.g. no duplicate `stroke-width`) or `addImage` silently fails —
  use the `ow()` helper pattern and keep `onerror` handlers.
- **MapLibre markers set inline opacity**: hide them with a class (`display:none` / child opacity), not
  container opacity.
- **Zoom in filters**: use `minzoom` on separate layers rather than `['zoom']` inside `filter`.
- **Cloudflare Pages is now Workers static assets**: deploy with `wrangler deploy` and `wrangler.toml [assets]`;
  `public/_headers` sets caching (`/data/*` 1 h, `/assets/*` immutable).
- The browser pane in a hidden tab throttles animation frames; slow first paint there is not a real bug.
- INEGI re-keys AGEBs when a municipio is created: join 2020 tables only to the 2020 census-edition
  outlines (`base.load_agebs_2020`), never to the live `wscatgeo` service.
- **SIAP has no rows for 25-020 yet** (cierres up to 2025): it still counts the town inside Guasave (011) and Ahome
  (001). Show those as whole-municipio tables in «Antes»; never split them over zones or fields. SIAP moved to
  `nube.agricultura.gob.mx` (the old `*.siap.gob.mx` hosts no longer resolve).
- **INEGI USV Serie VII**: INEGI's page only offers it through a JavaScript catalogue; `campo.py` reads CONABIO's
  unchanged copy of the national shapefile (317 MB zip, cached for years). A committed clip is the fallback.
- REPDA releases file wells under the old municipio codes: `water.py` keeps points by the 2025 municipio
  outline, not by `CLAVE DE MUNICIPIO`.

## Weekly Action (`.github/workflows/weekly-refresh.yml`)

Mondays 06:00 UTC: restore `pipeline/.cache`, drop OSM + iNaturalist caches, run
`hlm.run --skip blocks,streets`, commit `public/data`, build and `wrangler deploy`.
Repo secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, optional `PC_SDK_SUBSCRIPTION_KEY`.

## Analytics

Google Tag Manager `GTM-P3XKB934` in `index.html` (skipped on localhost) → GA4. Custom dataLayer events:
`cambio_modo`, `abrir_barrio`, `ver_ficha_punto` (tipo animal | negocio | pozo), `cambio_estilo`, `cambio_epoca` (see `src/analytics.ts`).

## Commits

Small, focused commits with a clear message. Never commit `.env`, tokens, `pipeline/.cache/`, or full national
source files. Regenerate `public/data/` with the pipeline rather than editing it by hand.
