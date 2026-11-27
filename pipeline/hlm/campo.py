"""Campo: where the farmland is and what the municipio grows.

Sources
- INEGI Uso del Suelo y Vegetación, escala 1:250 000, Serie VII (continuo nacional, 2018 imagery, published
  2021). The national shapefile is read from CONABIO's geoportal, which redistributes INEGI's set unchanged
  (INEGI's own page serves it only through a JavaScript catalogue). Only the agricultural classes
  (riego, temporal, …) are kept, clipped to the 2025 outline of municipio 25-020. If the download fails, a
  committed clip of the same polygons (`pipeline/manual/usv7_25020.geojson`) is used.
- ESA WorldCover 2021, class 40 "Cultivos" (10 m). Reuses the raster `green.py` caches for the municipio bbox.
  Satellite classification: the UI says «visto desde satélite».
- SIAP Cierre de la producción agrícola por municipio (open data CSV, nube.agricultura.gob.mx), the last three
  years. Shown exactly as published, for the whole municipio. SIAP still reports Juan José Ríos inside Guasave
  (25-011) and Ahome (25-001); when 25-020 has no rows the municipio view says «sin datos» and the
  «Antes de ser Municipio» view shows Guasave's and Ahome's tables, labelled as those whole municipios.

Rules
- Real data only: SIAP totals are never spread over zones or polygons (no crop-per-field map).
- Per zone, only `c_crop` = % of the zone's pixels WorldCover sees as cropland (modelled, satellite).
"""
from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from collections import Counter, defaultdict

import numpy as np

from .common import BBOX, CACHE, CITY_CENTER, ENT, MANUAL, MUN, OUT, Manifest, Provenance, SourceUnavailable, fetch, \
    local_area_km2, round_coords, write_json

# --- INEGI USV Serie VII ---
USV_URL = "http://www.conabio.gob.mx/informacion/gis/maps/geo/usv250s7gw.zip"
USV_PAGE = "http://geoportal.conabio.gob.mx/metadatos/doc/html/usv250s7gw.html"
USV_ZIP = "usv250s7gw.zip"
USV_CLIP = "usv7_25020.geojson"  # committed fallback: the same polygons, already clipped to the municipio
# INEGI agricultural classes (DESCRIPCIO / TIP_INFO). Each maps to the plain kind shown on the map.
AGRI_KINDS = ["riego", "temporal", "humedad"]  # order = legend order

# --- SIAP ---
SIAP_PAGE = "https://nube.agricultura.gob.mx/datosAbiertos/Agricola.php"
SIAP_CSV = "https://nube.agricultura.gob.mx/index.php?view=10AE434F-A2158368-A120BC5A-EDF4AFAA&ANIO={}"
SIAP_YEARS = 3
SIAP_MUNS = {"020": "Juan José Ríos", "011": "Guasave", "001": "Ahome"}

WC_CROP = 40  # ESA WorldCover class "Cropland"
IMG_W = 1600  # px across the municipio bbox (≈ 30 m per pixel)
CROP_RGB = (92, 84, 30)  # dark olive; legend uses the same colour


# ---------------------------------------------------------------- INEGI USV
def _kind(desc: str) -> str | None:
    d = desc.upper()
    if "AGRICULTURA" not in d and "AGRÍCOLA" not in d and "AGRICOLA" not in d:
        return None
    if "RIEGO" in d:
        return "riego"
    if "TEMPORAL" in d:
        return "temporal"
    if "HUMEDAD" in d:
        return "humedad"
    return "temporal"  # INEGI has no other agricultural water regime at 1:250 000


def _usv_from_zip(path, area) -> list[dict]:
    import shapefile  # pyshp
    from shapely.geometry import shape
    from shapely.prepared import prep
    z = zipfile.ZipFile(path)
    shp = next(n for n in z.namelist() if n.lower().endswith(".shp"))
    stem = shp[:-4]
    # pyshp reads from file objects; extract the three parts once next to the zip
    out = CACHE / "usv7"
    out.mkdir(exist_ok=True)
    for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
        member = next((n for n in z.namelist() if n.lower() == (stem + ext).lower()), None)
        dest = out / ("usv7" + ext)
        if member and not dest.exists():
            with z.open(member) as src, open(dest, "wb") as f:
                while chunk := src.read(1 << 22):
                    f.write(chunk)
    prj = (out / "usv7.prj").read_text(errors="ignore").lstrip() if (out / "usv7.prj").exists() else ""
    if prj and not prj.startswith("GEOGCS"):  # projected (Lambert): this file must be the geographic edition
        raise SourceUnavailable("USV zip is not in geographic coordinates")
    r = shapefile.Reader(str(out / "usv7"), encoding="latin-1")
    fields = [f[0] for f in r.fields[1:]]
    i_desc = next(i for i, f in enumerate(fields) if f.upper() in ("DESCRIPCIO", "DESCRIPCION"))
    i_tip = next((i for i, f in enumerate(fields) if f.upper() == "TIP_INFO"), None)
    bb = (BBOX[1], BBOX[0], BBOX[3], BBOX[2])
    inside = prep(area)
    feats = []
    for sr in r.iterShapeRecords(bbox=bb):
        rec = sr.record
        k = _kind(str(rec[i_desc]))
        if k is None:
            continue
        g = shape(sr.shape.__geo_interface__)
        if not g.is_valid:
            g = g.buffer(0)
        if not inside.intersects(g):
            continue
        g = g.intersection(area)
        if g.is_empty or g.area == 0:
            continue
        feats.append({"kind": k, "desc": str(rec[i_desc]).strip(), "tip": str(rec[i_tip]).strip() if i_tip is not None else "",
                      "geom": g})
    return feats


def _usv(manifest: Manifest, area) -> tuple[list[dict], dict]:
    prov = Provenance(id="inegi_usv7", name="Uso del Suelo y Vegetación, escala 1:250 000, Serie VII (zonas agrícolas)",
                      url=USV_PAGE, license="Términos de Libre Uso de la Información del INEGI",
                      publisher="INEGI (copia del continuo nacional en el geoportal de CONABIO)", vintage="Serie VII (2018), publicada 2021",
                      notes="Solo las clases de agricultura (riego, temporal), recortadas al municipio 25-020. Escala 1:250 000: "
                            "las orillas son aproximadas y las parcelas chicas no se ven.")
    feats = []
    try:
        feats = _usv_from_zip(fetch(USV_URL, USV_ZIP, max_age_days=3650, timeout=1800), area)
    except (SourceUnavailable, StopIteration, zipfile.BadZipFile, OSError, KeyError) as e:
        print(f"  ! USV Serie VII zip unavailable: {e}")
        clip = MANUAL / USV_CLIP
        if clip.exists():
            from shapely.geometry import shape
            print(f"  → using committed clip pipeline/manual/{USV_CLIP}")
            feats = [{"kind": f["properties"]["tipo"], "desc": f["properties"]["desc"], "tip": "",
                      "geom": shape(f["geometry"])} for f in json.loads(clip.read_text(encoding="utf-8"))["features"]]
            prov.notes += " (Leído de la copia recortada guardada en el proyecto.)"
        else:
            prov.status, prov.notes = "unavailable", str(e)
    if not feats:
        if prov.status == "ok":
            prov.status, prov.notes = "unavailable", "no agricultural polygons inside the municipio"
        manifest.add(prov)
        return [], {}

    out, ha = [], Counter()
    for f in feats:
        h = local_area_km2(f["geom"]) * 100
        ha[f["kind"]] += h
        g = f["geom"].simplify(0.0002, preserve_topology=True)  # ≈ 20 m: well under the 1:250 000 accuracy
        if g.is_empty:
            continue
        from shapely.geometry import mapping
        out.append({"type": "Feature", "geometry": round_coords(mapping(g), 5),
                    "properties": {"tipo": f["kind"], "desc": f["desc"].capitalize(), "ha": round(h)}})
    out.sort(key=lambda x: -x["properties"]["ha"])
    write_json(OUT / "campo.geojson", {"type": "FeatureCollection", "kinds": AGRI_KINDS, "features": out})
    manifest.add(prov)
    total = sum(ha.values())
    print(f"  USV VII: {len(out)} agricultural polygons, {total:,.0f} ha ({', '.join(f'{k} {v:,.0f}' for k, v in ha.items())})")
    return out, {"ha": round(total), "kinds": {k: round(ha[k]) for k in AGRI_KINDS if ha[k]}, "n": len(out)}


# ---------------------------------------------------------------- ESA WorldCover cropland
def _cropland(manifest: Manifest, agebs: list[dict], area) -> dict:
    from rasterio.features import rasterize
    from rasterio.warp import transform_geom
    from shapely.geometry import mapping
    from . import green
    from .heat import UTM

    prov = Provenance(id="esa_worldcover_cultivos", name="ESA WorldCover 2021 — cultivos (clase 40, 10 m)",
                      url="https://planetarycomputer.microsoft.com/dataset/esa-worldcover", license="CC-BY 4.0",
                      publisher="ESA WorldCover consortium (vía Microsoft Planetary Computer)", vintage="2021", modeled=True,
                      notes="Clasificación automática de imágenes de satélite: lo que se ve sembrado, no un registro de parcelas.")
    try:
        T10, w10, h10 = green._grid(10.0)
        cache = CACHE / "worldcover_2021_10m.npy"
        if cache.exists():
            lc = np.load(cache)
        else:
            tok = green._json(green.TOKEN.format("esa-worldcover"))["token"]
            lc = green._worldcover(T10, w10, h10, tok)
        if lc.shape != (h10, w10):
            raise SourceUnavailable(f"cached WorldCover grid {lc.shape} != {(h10, w10)}")
    except Exception as e:  # noqa: BLE001 - satellite outage must not stop the run
        print(f"  ! WorldCover unavailable: {e}")
        prov.status, prov.notes = "unavailable", str(e)
        manifest.add(prov)
        for a in agebs:
            a["c_crop"] = None
        return {}

    mun = rasterize([(transform_geom("EPSG:4326", UTM, mapping(area)), 1)], out_shape=(h10, w10), transform=T10,
                    fill=0, dtype="uint8").astype(bool)
    crop = lc == WC_CROP
    valid = lc > 0
    ha_crop = float((crop & mun).sum()) * 0.01  # one 10 m pixel = 0.01 ha
    ha_mun = float((valid & mun).sum()) * 0.01

    ids = rasterize([(transform_geom("EPSG:4326", UTM, mapping(a["geom"])), i + 1) for i, a in enumerate(agebs)],
                    out_shape=(h10, w10), transform=T10, fill=0, dtype="int32")
    n = len(agebs) + 1
    s = np.bincount(ids[valid], weights=crop[valid].astype("float64"), minlength=n)
    c = np.bincount(ids[valid], minlength=n)
    for i, a in enumerate(agebs):
        a["c_crop"] = round(float(100 * s[i + 1] / c[i + 1]), 1) if c[i + 1] >= 5 else None

    # overlay picture: share of cropland pixels in each ~30 m cell, inside the municipio only
    from PIL import Image
    from rasterio.enums import Resampling
    from rasterio.transform import from_bounds
    from rasterio.warp import reproject
    w_deg, so, e, no = BBOX[1], BBOX[0], BBOX[3], BBOX[2]
    W = IMG_W
    H = int(W * (no - so) / ((e - w_deg) * np.cos(np.radians(CITY_CENTER[0]))))
    frac = np.zeros((H, W), dtype="float32")
    src = np.where(mun & valid, crop.astype("float32"), np.nan).astype("float32")
    reproject(src, frac, src_transform=T10, src_crs=UTM, dst_transform=from_bounds(w_deg, so, e, no, W, H),
              dst_crs="EPSG:4326", resampling=Resampling.average, src_nodata=np.nan, dst_nodata=0)
    alpha = np.clip(np.nan_to_num(frac) * 255, 0, 255).astype("uint8")
    rgb = np.broadcast_to(np.array(CROP_RGB, dtype="uint8"), (H, W, 3))
    Image.fromarray(np.dstack([rgb, alpha]), "RGBA").save(OUT / "campo.png", optimize=True)
    print(f"  wrote public/data/campo.png ({(OUT / 'campo.png').stat().st_size / 1e6:.2f} MB)")
    manifest.add(prov)
    print(f"  WorldCover: {ha_crop:,.0f} ha of cropland = {100 * ha_crop / ha_mun:.0f}% of the municipio")
    return {"ha": round(ha_crop), "p_mun": round(100 * ha_crop / ha_mun, 1), "year": 2021,
            "image": {"file": "campo.png", "bounds": [w_deg, so, e, no]}}


# ---------------------------------------------------------------- SIAP
def _siap_years() -> dict[int, str]:
    """{year: csv url} of the municipal 'Cierre' files listed on SIAP's open-data page."""
    try:
        html = fetch(SIAP_PAGE, "siap_datos_abiertos_agricola.html", max_age_days=6).read_text(encoding="utf-8", errors="ignore")
    except SourceUnavailable:
        html = ""
    found = {int(y): "https://nube.agricultura.gob.mx" + href.replace("&amp;", "&")
             for y, href in re.findall(r'title="Descargar informaci[^"]*municipal del a[^"]*?(\d{4})"\s+href="([^"]+)"', html)}
    if not found:  # page layout changed or offline: use the known link pattern and manual copies
        found = {y: SIAP_CSV.format(y) for y in range(2003, 2100)
                 if (MANUAL / f"siap_cierre_mun_{y}.csv").exists() or (CACHE / f"siap_cierre_mun_{y}.csv").exists()}
    return dict(sorted(found.items())[-SIAP_YEARS:])


def _read_siap(path) -> list[dict]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")
    return [r for r in csv.DictReader(io.StringIO(text)) if r.get("Idestado", "").strip() == str(int(ENT))]


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _summary(rows: list[dict]) -> dict:
    crops = defaultdict(lambda: {"sem": 0.0, "cos": 0.0, "sin": 0.0, "val": 0.0, "riego": 0.0, "units": Counter(), "prod": defaultdict(float)})
    tot = Counter()
    for r in rows:
        k = r["Nomcultivo"].strip()
        c = crops[k]
        sem, cos, sin, val = (_num(r[x]) for x in ("Sembrada", "Cosechada", "Siniestrada", "Valorproduccion"))
        u = r["Nomunidad"].strip()
        c["sem"] += sem
        c["cos"] += cos
        c["sin"] += sin
        c["val"] += val
        c["units"][u] += 1
        c["prod"][u] += _num(r["Volumenproduccion"])
        riego = r["Nommodalidad"].strip().lower().startswith("riego")
        if riego:
            c["riego"] += sem
        tot["sem"] += sem
        tot["cos"] += cos
        tot["sin"] += sin
        tot["val"] += val
        tot["riego" if riego else "temporal"] += sem
        tot["oi" if r["Nomcicloproductivo"].startswith("Oto") else "pv" if r["Nomcicloproductivo"].startswith("Primavera") else "per"] += sem
    out = []
    for name, c in crops.items():
        unit = c["units"].most_common(1)[0][0]
        # [crop, sown ha, harvested ha, lost ha, production, unit, value in pesos, % of sown area under irrigation]
        out.append([name, round(c["sem"]), round(c["cos"]), round(c["sin"]), round(c["prod"][unit]), unit, round(c["val"]),
                    round(100 * c["riego"] / c["sem"]) if c["sem"] else None])
    out.sort(key=lambda x: -x[2])
    return {"totals": {k: round(v) for k, v in tot.items()}, "n_crops": len(out), "crops": out[:10]}


def _siap(manifest: Manifest) -> dict:
    years = _siap_years()
    per = {m: {} for m in SIAP_MUNS}
    got = []
    for y, url in years.items():
        name = f"siap_cierre_mun_{y}.csv"
        try:
            rows = _read_siap(fetch(url, name, max_age_days=30 if y == max(years) else 365, timeout=600))
        except (SourceUnavailable, KeyError) as e:
            print(f"  ! SIAP {y}: {e}")
            continue
        if not rows or "Nomcultivo" not in rows[0]:
            continue
        got.append(y)
        by_mun = defaultdict(list)
        for r in rows:
            by_mun[r["Idmunicipio"].strip().zfill(3)].append(r)
        for m in SIAP_MUNS:
            per[m][y] = _summary(by_mun[m]) if by_mun.get(m) else None
    if not got:
        manifest.add(Provenance(id="siap_cierre_agricola", name="Cierre de la producción agrícola por municipio", url=SIAP_PAGE,
                                license="Términos de Libre Uso MX", publisher="SIAP — Secretaría de Agricultura y Desarrollo Rural",
                                vintage="?", status="unavailable", notes="no SIAP file could be read"))
        return {}
    latest = max(got)
    mun = {}
    for m, name in SIAP_MUNS.items():
        last = per[m].get(latest)
        mun[m] = None if last is None else {
            "name": name, "year": latest, **last,
            "series": [[y, per[m][y]["totals"]["sem"], per[m][y]["totals"]["cos"], per[m][y]["totals"]["val"]]
                       for y in sorted(got) if per[m].get(y)],
        }
    have_own = mun[MUN] is not None
    manifest.add(Provenance(
        id="siap_cierre_agricola", name="Cierre de la producción agrícola por municipio (datos abiertos)", url=SIAP_PAGE,
        license="Términos de Libre Uso MX", publisher="SIAP — Secretaría de Agricultura y Desarrollo Rural",
        vintage=f"cierres {min(got)}–{latest}",
        notes=("Cifras del municipio tal como las publica el SIAP." if have_own else
               f"El SIAP todavía no publica a {SIAP_MUNS[MUN]} (25-{MUN}) por separado: sus siembras van dentro de Guasave "
               "y Ahome. Esos totales son de los municipios completos y se muestran en «Antes de ser Municipio».")))
    for m in SIAP_MUNS:
        t = mun[m]
        print(f"  SIAP {latest} {SIAP_MUNS[m]}: " + (f"{t['totals']['sem']:,} ha sembradas, {t['n_crops']} cultivos, "
                                                     f"${t['totals']['val'] / 1e6:,.0f} millones" if t else "sin datos"))
    return {"years": sorted(got), "latest": latest, "mun": mun}


# ---------------------------------------------------------------- entry point
def build_campo(manifest: Manifest, agebs: list[dict], area) -> dict:
    _, usv = _usv(manifest, area)
    crop = _cropland(manifest, agebs, area)
    siap = _siap(manifest)
    own = siap.get("mun", {}).get(MUN) if siap else None
    parts = [("inegi_usv7", usv), ("esa_worldcover_cultivos", crop), ("siap_cierre_agricola", own)]
    srcs = [s for s, ok in parts if ok]
    if not usv and not crop:
        manifest.layer("campo", "unavailable", [s for s, _ in parts])
        return {"siap": siap} if siap else {}
    manifest.layer("campo", "ok" if all(ok for _, ok in parts) else "partial", srcs)
    return {"usv": usv or None, "cropland": crop or None, "siap": siap or None}


def antes_siap(manifest: Manifest, campo: dict | None) -> dict | None:
    """«Antes de ser Municipio»: the SIAP tables of the two municipios the town belonged to (011, 001)."""
    siap = (campo or {}).get("siap")
    if not siap:
        manifest.layer("antes_campo", "unavailable", ["siap_cierre_agricola"])
        return None
    out = {"years": siap["years"], "latest": siap["latest"], "mun": {m: siap["mun"].get(m) for m in ("011", "001")}}
    ok = any(out["mun"].values())
    manifest.layer("antes_campo", "ok" if ok else "unavailable", ["siap_cierre_agricola"])
    return out if ok else None
