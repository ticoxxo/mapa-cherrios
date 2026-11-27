# Datos — Juan José Ríos: El Mapa Vivo

Every number in the app comes from an open, citable source. Each pipeline run writes
`public/data/manifest.json` with the source URL, license, vintage, retrieval date and status of
every input; the in-app "Créditos de datos" table is rendered from it. When a source fails, its
layer is marked `unavailable` and the UI says **"Datos no disponibles"**: no placeholder values.

Spatial unit: INEGI **AGEB urbana** (key `CVEGEO`, 13 characters). Sinaloa = `25`.

## Two views and why the census is only in one

Juan José Ríos became municipio `25-020` by the 2021 decree of the Sinaloa Congress (amended 2023). In the 2020
census the town was localidad `0138` of **Guasave** (`011`) and El Estero (Juan José Ríos) was localidad `0136` of
**Ahome** (`001`). INEGI re-keyed every AGEB for the new municipio: none of the 19 + 1 census AGEBs share a key
with the 15 AGEBs of the Dec 2025 framework. So:

- **Municipio** (`public/data/`): Dec 2025 AGEBs of `25/020` with every live layer. Census-based figures are
  *not* shown there (no re-apportioning of 2020 blocks into new zones); the app points to the other view.
- **Antes de ser Municipio** (`public/data/antes/`): AGEBs and blocks of the Marco Geoestadístico 2020 census
  edition, joined to the Censo 2020 by their own `CVEGEO` (20 of 20 AGEBs, 324 of 329 blocks with an outline).
  Only 2020 data is shown there.

## Status of each dataset

| Mode / layer | Dataset | Publisher | Vintage | Update frequency | License | Status |
|---|---|---|---|---|---|---|
| Base (Municipio): AGEBs, blocks, streets, municipio outline | Marco Geoestadístico (`wscatgeo/v2/geo/{agebu,mza,vialidades,mgem}/25/020`) | INEGI | Dec 2025 | Yearly | INEGI Términos de libre uso | **Built**: 15 AGEBs, 761 blocks, 1,988 street segments |
| Base (Antes): AGEBs, blocks | Marco Geoestadístico 2020, census edition (`889463807469/25_sinaloa.zip`, shapefiles `25a`, `25m`) | INEGI | 2020 | Static | INEGI Términos de libre uso | **Built**: 20 AGEBs, 324 blocks |
| Locality names | Catálogo Único de Claves Geoestadísticas (`wscatgeo/v2/localidades/25/020`) | INEGI | 2025 | Yearly | INEGI Términos de libre uso | **Built** |
| Base: landmarks, water, parks, place names | OpenStreetMap via Overpass (bbox 25.44–25.96 N, −109.13 to −108.64) | OSM contributors | live | Weekly | ODbL 1.0 | **Built**: 91 landmarks; OSM has no named neighbourhoods here |
| Base: sea | Natural Earth 1:10m ocean, clipped to the map area **minus INEGI's municipio outline** (at 1:10 M the nearby bays spill onto farmland) | Natural Earth | v5.1 | Static | Public domain | **Built** |
| Base: hillshade | AWS Terrain Tiles | Mapzen / AWS Open Data | static | — | Attribution | **Live tiles** |
| Territorios | k-means of AGEB centroids (population-weighted in the 2020 view, area-weighted today) | derived | — | Per run | CC-BY 4.0 (derived) | **Built — a visual grouping, not official districts** |
| People (Antes) | Censo 2020, AGEB y manzana urbana (`ageb_mza_urbana_25_cpv2020_csv.zip`), Guasave 0138 + Ahome 0136 | INEGI | 2020 | Decennial (next: 2030) | INEGI Términos de libre uso | **Built**: 26,664 people (22,421 + 4,243) |
| People (Municipio) | — | — | — | — | — | **Not shown**: no census yet with the new keys |
| Wealth (Antes) | CONAPO IMU 2020 and CONEVAL GRS 2020 by AGEB | CONAPO / CONEVAL | 2020 | Each census | CC-BY 4.0 | **Built** from hand-downloaded copies in `pipeline/manual/` (portals answer 403 to scripts), trimmed to the two localities: IMU for 14 of 20 AGEBs, GRS for 17 |
| Heat | Landsat 8/9 C2 L2 surface temperature via Planetary Computer; path/row chosen automatically (033/042); **May–Sep** 2023–2025; scene cloud < 30 %, per-pixel QA mask | USGS / NASA | 35 scenes | Yearly | Public domain | **Built**: AGEB means 44.4–48.8 °C |
| Heat (HUD) | NASA POWER daily T2M_MAX at 25.757, −108.822 | NASA | daily | Weekly | Public domain | **Built** (reanalysis, *modelado*) |
| Green | Sentinel-2 L2A NDVI, last 30 days and the same window a year earlier | Copernicus / ESA | weekly | Weekly | Copernicus open licence | **Built**: 15 passes now, 22 a year ago; 44 % of the town looks green |
| Green | ESA WorldCover 2021 v200 | ESA | 2021 | Static | CC-BY 4.0 | **Built**: 11.7 % tree cover, 481 cartoon trees |
| Wildlife | iNaturalist research-grade animals in the bbox, open licences only | iNaturalist | live | Weekly | Per observation | **Built**: 5,208 licensed, 4,968 drawn, 26 inside urban AGEBs |
| Work | DENUE Sinaloa (`denue_25_csv.zip`, `CVE_MUN = 020`; DENUE already uses the new municipio) | INEGI | edition 11/2026 | Twice a year; checked weekly | INEGI Términos de libre uso | **Built**: 1,756 businesses, ~9,456 jobs (*estimate*); 97 outside urban AGEBs |
| Water | REPDA (Zenodo copy of CONAGUA's releases); points kept by the **2025 municipio outline** (older releases file them under Guasave / Ahome) | CONAGUA | release 2025-06 | Irregular; checked weekly | Términos de Libre Uso MX | **Built**: 72 points (40 wells, 32 intakes), 5.7 hm³/year authorised |
| Water | Monitor de Sequía, municipal table, row `25020` | SMN / CONAGUA | every 15 days | Twice a month | Términos de Libre Uso MX | **Built**: sin sequía since 2026-06-15 |
| Campo | Uso del Suelo y Vegetación 1:250 000 Serie VII, national shapefile (CONABIO copy `usv250s7gw.zip`), agricultural classes clipped to 25-020 | INEGI | 2018 imagery, pub. 2021 | Static (Serie VIII when published) | INEGI Términos de libre uso | **Built**: 4 polygons, 40,549 ha (riego 37,190, temporal 3,360) |
| Campo | ESA WorldCover 2021 v200, class 40 (cropland) | ESA | 2021 | Static | CC-BY 4.0 | **Built** (*visto desde satélite*): 34,084 ha = 46 % of the municipio |
| Campo | SIAP Cierre de la producción agrícola por municipio (open-data CSV), last 3 years | SIAP / SADER | cierres 2023–2025 | Yearly; checked monthly | Términos de Libre Uso MX | **Built** for Guasave and Ahome (shown in «Antes»); **no rows for 25-020 yet** |
| Water (tinacos) | Censo 2020 `VPH_TINACO` | INEGI | 2020 | Decennial | INEGI Términos de libre uso | **Antes only**: in the Municipio view zones stay uncoloured and the legend says why |

## How figures are handled

- **Confidential cells:** INEGI `*` → `null`, shown as "—", never 0. A real `0` stays 0.
- **Derived ratios** come only from census counts (see below); areas use a local equirectangular projection.
- **Territorios** are a game construct; compass titles scale to the town (centre = inner quarter of its radius).
- **Descriptions** of a barrio use only that AGEB's own values; today's zones are described only with live data.

## Census percentages (audited 2026-11-26)

| Shown as | Numerator | Denominator | Why that denominator |
|---|---|---|---|
| Hogares con internet / troca / computadora / agua / drenaje | `VPH_INTER`, `VPH_AUTOM`, `VPH_PC`, `VPH_AGUADV`, `VPH_DRENAJ` | `VIVPARH_CV` | The `VPH_*` counts include dwellings without occupant information; `VIVPARH_CV` is the only total that includes them too |
| Casas vacías | `VIVPAR_DES` | `TVIVPAR` | Private dwellings only (`VIVTOT` adds collective housing) |
| Con trabajo (de quienes trabajan o buscan) | `POCUPADA` | `PEA` | INEGI's labour-force base |
| Sin servicio médico, edades | `PSINDER`, `POB0_14`, `POB15_64`, `POB65_MAS` | `POBTOT` | |
| Casas con gente (count) | `TVIVPARHAB` | | Full count of inhabited private dwellings |

An earlier version divided the `VPH_*` counts by `VIVPAR_HAB`, which excludes dwellings without occupant
information, and showed values up to 540 %. The pipeline now stops if any share falls outside 0–100 %
(`people.check_ratios`).

## Fauna rules

- **Only openly licensed observations** are used ("all rights reserved" observations are excluded). Each point keeps
  its observer's iNaturalist username and licence, shown on the sighting card with a link to the original.
- **Hidden locations stay hidden.** iNaturalist blurs coordinates of threatened species and private observations
  . They count in totals but are never drawn or assigned to a barrio.
- Positions less precise than 500 m are drawn but not counted for a barrio.
- **Counts measure observer effort, not wildlife abundance.** Places where more people take photos get more reports. The legend says so in plain words.
- "New this week" = observations **uploaded** in the last 7 days (an upload can be of an older sighting).
- La Gaceta's weekly entries come from `public/data/history.json` (one snapshot per ISO week) and are only
  generated from those numbers.

## Calor rules

- Landsat measures **land-surface temperature** (ground, roofs, pavement) at the ~10:40 local overpass, **not air
  temperature**. Values in the mid-40s °C are normal here in summer. The UI says "suelo y techos, no del aire".
- Clouds, cloud shadows and cirrus are removed per pixel with `QA_PIXEL`. Scenes less than 50 % clear over the map area
  are dropped (the Sinaloa summer is the rainy season). The composite is the per-pixel median of the remaining scenes, so a single odd day does not dominate.
- Per AGEB: mean of composite pixels whose centre falls inside the AGEB (at least 3 pixels).
- The HUD's "Máxima" is NASA POWER reanalysis at a ~0.5° cell: one value for the whole town, arriving a few days late.

## Verde rules

- **NDVI now** = per-pixel median of clear Sentinel-2 observations in the last 30 days (20 m). Clouds, shadows,
  cirrus and dark pixels are removed with the SCL scene classification. Reflectance uses the −1000 BOA offset for
  processing baseline ≥ 04.00.
- **A year ago** = the same 30-day window one year earlier, so the comparison isn't distorted by seasons. Weekly
  changes per territory come from `history.json` from the second weekly run on.
- **"Se ve verde"** = share of pixels with NDVI ≥ 0.3 (living, irrigated vegetation or trees in this climate).
- **Trees** = WorldCover 2021 class 10. One cartoon tree per 60 m cell that is ≥ 25 % tree cover, inside barrios,
  sized by that spot's current NDVI. It is **not a tree inventory**; the UI says so.

## Chamba rules

- **Businesses** come from DENUE and are assigned to an AGEB by DENUE's own `CVE_LOC` + `CVE_AGEB`, not by geometry.
  97 businesses have no urban AGEB; they are still drawn on the map.
- **Jobs are an estimate.** DENUE only gives a size range (`PER_OCU`). Each business counts as the midpoint:
  0–5 → 3, 6–10 → 8, 11–30 → 20, 31–50 → 40, 51–100 → 75, 101–250 → 175, 251+ → 300 (a deliberately low
  guess for the open range). The legend, ficha and Gaceta all say "cerca de" / "cálculo".
- **Colour** = estimated jobs per km² (where people work, not where they live), six quantile classes.
- **Groups** by the first two SCIAN digits: tiendas (43, 46), comida (72), talleres (81), oficinas (51–56, 93),
  fábricas/obras/bodegas (11, 21–23, 31–33, 48–49), escuelas/salud/diversión (61, 62, 71).
- Only the name, activity, size range and month the business entered the directory are published. Phones,
  e-mails, web sites and street addresses are not copied into the app.
- Informal work (street stalls without a fixed place, work from home) is not in DENUE; the legend says so.
- La Gaceta writes Chamba entries only when INEGI publishes a new edition (or the first time).

## Agua rules

- **Water rights** come from REPDA. `datos.conagua.gob.mx` answers scripts with a bot wall (Incapsula), so the
  pipeline reads the newest release in the Zenodo record that preserves CONAGUA's own archives unmodified
  (`repda_zenodo_record.json` is re-checked every 6 days; each `REPDA_YYYY-MM.zip` is cached for good). Don't
  try to get past the bot wall; a hand-downloaded `pipeline/manual/REPDA_YYYY-MM.zip` is the fallback.
- Points are wells (`ANEXOS_SUBTERRANEOS*`) and surface intakes (`ANEXOS_SUPERFICIALES*`) in state 25 whose
  coordinates fall inside INEGI's 2025 outline of municipio 25-020. Points without coordinates cannot be
  placed in the new municipio and are left out.
- **Volumes are what each title authorises per year, not what is pumped.** Legend, card, ficha and Gaceta say so.
  "Albercas olímpicas" = volume ÷ 2,500 m³, rounded.
- **Uses**: AGRÍCOLA → campo; PÚBLICO URBANO → ciudad; INDUSTRIAL, AGROINDUSTRIAL, GENERACIÓN DE ENERGÍA → industria;
  PECUARIO → ganado; everything else (DIFERENTES USOS, SERVICIOS, DOMÉSTICO…) → otros.
- **Privacy**: a holder is named only if it looks like a company, ejido, association or public body
  (`water.is_entity`: legal suffixes S.A., S.P.R., S. de R.L., A.C., SAPI…, or words like EJIDO, MUNICIPIO,
  COMISIÓN). Everyone else is "Particular" and their point is rounded to 3 decimals
  (~100 m). Top-holder lists merge spellings of the same company (`water.holder_key`).
- **Drought**: in the SMN table an empty cell means *sin sequía* (its NOTAS sheet says so), so it is level 0,
  not missing. Levels: sin, D0 anormalmente seco, D1–D4 moderada → excepcional. Missing reports (Aug 2003,
  Feb 2004) are simply absent columns.
- **Colour** = % of homes with a tinaco (`VPH_TINACO / VIVPARH_CV`), six quantile classes. Cisterns are too rare
  (median 2 %) to colour the map; they are shown in the ficha.
- La Gaceta writes Agua entries when the drought level changes or a new REPDA release appears (or the first time).

## Campo rules

- **Where the farmland is**: two independent sources, drawn on top of each other and never mixed:
  - INEGI **Uso del Suelo y Vegetación, Serie VII** (1:250 000, 2018 imagery, published 2021). INEGI's own page
    serves it only through a JavaScript catalogue, so `campo.py` reads the unchanged national shapefile that
    CONABIO's geoportal redistributes (`usv250s7gw.zip`, geographic coordinates, 317 MB, cached for years).
    Polygons whose `DESCRIPCIO` says *agricultura* are kept and grouped by water regime (riego, temporal,
    humedad), clipped to INEGI's 2025 outline of 25-020, simplified to ≈ 20 m. At 1:250 000 the edges are
    approximate and small plots don't show: the card and legend say so. Fallback: the committed clip
    `pipeline/manual/usv7_25020.geojson`.
  - ESA **WorldCover 2021 class 40** (cropland, 10 m), the same raster `green.py` caches. Drawn as `campo.png`
    (share of cropland pixels per ≈ 30 m cell, inside the municipio only). It is a satellite classification, so the
    UI says «visto desde satélite» and the manifest marks it `modeled`.
- **Per zone** there is only `c_crop`: % of the barrio's WorldCover pixels that are cropland (≥ 5 pixels, else
  `null`). Barrios are town, so the colour uses fixed breaks 1 / 5 / 15 / 40 % instead of quantiles.
- **What is grown**: SIAP *Cierre de la producción agrícola por municipio* (open-data CSV from
  `nube.agricultura.gob.mx`; the old `*.siap.gob.mx` hosts no longer resolve). The last three published years
  are read; the newest is refreshed monthly. Per municipio and year: sown / harvested / lost hectares, production
  and value (pesos) by crop, summed over cycles (otoño-invierno, primavera-verano, perennes) and water regimes.
  Production is summed only in the crop's most common unit. Figures are shown **exactly as published**.
- **SIAP has no rows for 25-020** (checked up to the 2025 cierre): it still counts the town inside Guasave (011)
  and Ahome (001). The Municipio view then says «sin datos» and points to «Antes de ser Municipio», where Campo shows
  only Guasave's and Ahome's tables, labelled as **whole municipios**. The map stays on the plain zones there.
  The tables are never split over zones or fields: there is no per-field crop map.
- La Gaceta writes a Campo entry when a new SIAP cierre year appears (or the first time), from 25-020 if it exists,
  otherwise from Guasave, saying so.

## Known gaps

- **No census for the new municipio yet.** The next one (2030) will use the new keys; until then census figures
  live only in "Antes de ser Municipio".
- **CONAPO / CONEVAL** answer 403 to scripts: the committed copies in `pipeline/manual/` were downloaded in a
  browser and trimmed to Guasave 0138 + Ahome 0136. Zones with very few people carry no index.
- **No public tree inventory**; Verde draws trees from WorldCover and says so.
- **No crop map per field.** SIAP publishes crops only per municipio, and not yet for 25-020; INEGI's farmland
  polygons say only riego / temporal. Campo shows each source as it is and never spreads one over the other.
- **No named neighbourhoods in OSM** for the town, so territorios carry only compass titles.
- **NASA POWER weather** is one value for the whole town (HUD only).
