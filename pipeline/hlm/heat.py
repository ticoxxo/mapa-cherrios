"""Calor: summer land-surface temperature (Landsat 8/9 Collection 2 Level-2, ST_B10) per AGEB,
plus NASA POWER daily maximum air temperature for the HUD.

Source access: Microsoft Planetary Computer STAC (public; anonymous SAS token for the blobs).
Optional env var PC_SDK_SUBSCRIPTION_KEY raises rate limits. Never commit keys.

Method
- Scenes: WRS path 035 / row 040 (covers the whole city), June–August of SUMMERS, scene cloud
  cover < MAX_CLOUD %. Per pixel, QA_PIXEL masks fill, dilated cloud, cirrus, cloud and shadow.
- LST °C = DN × 0.00341802 + 149.0 − 273.15 (USGS C2 L2 scale factors).
- Summer composite = per-pixel median across all clear scenes, on a fixed 30 m UTM 12N grid.
- Per AGEB: mean of composite pixels whose centre falls inside the AGEB.
This is the temperature of the ground and roofs, not of the air. The UI says so.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.parse
import urllib.request

import numpy as np

from .common import BBOX, CITY_CENTER, OUT, PLACE, TODAY, UA, Manifest, Provenance, write_json

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
TOKEN = "https://planetarycomputer.microsoft.com/api/sas/v1/token/landsat-c2-l2"
SUMMERS = (2023, 2024, 2025)
# Sinaloa's summer is the rainy season: allow cloudier scenes (clouds are masked per pixel with QA_PIXEL)
# and use May–September, the hottest months.
MAX_CLOUD = 30
SEASON = ("05-01", "09-30")
SEASON_ES = "may–sep"
UTM = "EPSG:32612"
RES = 30.0
SCALE, OFFSET = 0.00341802, 149.0
# QA_PIXEL bits: 0 fill, 1 dilated cloud, 2 cirrus, 3 cloud, 4 cloud shadow
QA_BAD = (1 << 0) | (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4)
POWER = "https://power.larc.nasa.gov/api/temporal/daily/point"


def _json(url: str, body: dict | None = None) -> dict:
    headers = {"User-Agent": UA, "Content-Type": "application/json"}
    if os.environ.get("PC_SDK_SUBSCRIPTION_KEY") and "planetarycomputer" in url:
        headers["Ocp-Apim-Subscription-Key"] = os.environ["PC_SDK_SUBSCRIPTION_KEY"]
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def _scenes() -> list[dict]:
    items = []
    for y in SUMMERS:
        d = _json(STAC, {
            "collections": ["landsat-c2-l2"],
            "bbox": [BBOX[1], BBOX[0], BBOX[3], BBOX[2]],
            "datetime": f"{y}-{SEASON[0]}T00:00:00Z/{y}-{SEASON[1]}T23:59:59Z",
            "query": {"eo:cloud_cover": {"lt": MAX_CLOUD}, "platform": {"in": ["landsat-8", "landsat-9"]}},
            "limit": 100,
        })
        items += d["features"]
    # keep one WRS path/row (a consistent footprint): the one covering the town centre most often
    from collections import Counter

    from shapely.geometry import Point, shape
    centre = Point(CITY_CENTER[1], CITY_CENTER[0])
    pr = lambda f: (f["properties"].get("landsat:wrs_path"), f["properties"].get("landsat:wrs_row"))  # noqa: E731
    covering = [f for f in items if shape(f["geometry"]).contains(centre)]
    if not covering:
        return []
    best = Counter(pr(f) for f in covering).most_common(1)[0][0]
    global PATH_ROW
    PATH_ROW = best
    items = [f for f in covering if pr(f) == best]
    items.sort(key=lambda f: f["properties"]["datetime"])
    return items


PATH_ROW: tuple = ("?", "?")  # set by _scenes()


def _grid():
    """Fixed 30 m UTM grid covering the city bbox."""
    from rasterio.transform import from_origin
    from rasterio.warp import transform_bounds
    left, bottom, right, top = transform_bounds("EPSG:4326", UTM, BBOX[1], BBOX[0], BBOX[3], BBOX[2])
    left, top = np.floor(left / RES) * RES, np.ceil(top / RES) * RES
    w, h = int(np.ceil((right - left) / RES)), int(np.ceil((top - bottom) / RES))
    return from_origin(left, top, RES, RES), w, h


def _read(href: str, transform, w: int, h: int) -> np.ndarray:
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.vrt import WarpedVRT
    with rasterio.open(href) as src, WarpedVRT(src, crs=UTM, transform=transform, width=w, height=h,
                                                resampling=Resampling.nearest, nodata=0) as vrt:
        return vrt.read(1)


def build_heat(manifest: Manifest, agebs: list[dict]) -> dict:
    """Cached wrapper: the summer composite only changes when SUMMERS changes."""
    from .common import CACHE
    cache = CACHE / "heat_result.json"
    if cache.exists() and (OUT / "heat.png").exists():
        c = json.loads(cache.read_text(encoding="utf-8"))
        if c.get("summers") == list(SUMMERS) and c.get("prov"):
            for a in agebs:
                a["lst"] = c["lst"].get(a["cvegeo"])
            manifest.sources["landsat_lst"] = c["prov"]
            manifest.layer("heat", "ok", ["landsat_lst", "nasa_power"])
            print(f"  heat: reused cached composite ({c['stats']['n_scenes']} scenes)")
            return c["stats"]
    stats = _build_heat(manifest, agebs)
    if stats:
        CACHE.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"summers": list(SUMMERS), "stats": stats, "prov": manifest.sources["landsat_lst"],
                                     "lst": {a["cvegeo"]: a["lst"] for a in agebs}}), encoding="utf-8")
    return stats


def _build_heat(manifest: Manifest, agebs: list[dict]) -> dict:
    import rasterio
    from rasterio.features import rasterize
    from rasterio.warp import transform_geom
    from shapely.geometry import mapping

    prov = Provenance(id="landsat_lst", name="Temperatura de la superficie, veranos " + "–".join(map(str, (SUMMERS[0], SUMMERS[-1]))),
                      url="https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2",
                      license="Dominio público (USGS)", publisher="USGS / NASA — Landsat 8 y 9 (vía Microsoft Planetary Computer)",
                      vintage=f"{SEASON_ES} {SUMMERS[0]}–{SUMMERS[-1]}")
    try:
        items = _scenes()
        token = _json(TOKEN)["token"]
    except Exception as e:  # noqa: BLE001
        prov.status, prov.notes = "unavailable", str(e)
        manifest.add(prov)
        manifest.layer("heat", "unavailable", ["landsat_lst"], reason=str(e))
        for a in agebs:
            a["lst"] = None
        return {}

    transform, w, h = _grid()
    from .common import CACHE
    comp_cache = CACHE / f"heat_comp_{SUMMERS[0]}_{SUMMERS[-1]}.npz"
    if comp_cache.exists():
        z = np.load(comp_cache)
        comp, used = z["comp"], [str(x) for x in z["used"]]
        print(f"  heat: reusing cached composite of {len(used)} scenes")
        return _finish(manifest, agebs, prov, comp, used, transform, w, h)
    stack, used = [], []
    env = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".TIF,.tif",
               GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2", VSI_CACHE="TRUE")
    with rasterio.Env(**env):
        for it in items:
            sign = lambda href: f"{href}?{token}"  # noqa: E731
            try:
                st = _read(sign(it["assets"]["lwir11"]["href"]), transform, w, h).astype("float32")
                qa = _read(sign(it["assets"]["qa_pixel"]["href"]), transform, w, h)
            except Exception as e:  # noqa: BLE001
                print(f"  ! skipped {it['id']}: {e}")
                continue
            lst = st * SCALE + OFFSET - 273.15
            bad = (st == 0) | ((qa & QA_BAD) != 0)
            lst[bad] = np.nan
            clear = 1 - np.isnan(lst).mean()
            if clear < 0.5:  # too cloudy over the map area
                continue
            stack.append(lst)
            used.append(it["properties"]["datetime"][:10])
            print(f"  Landsat {it['properties']['platform']} {used[-1]}: {clear:.0%} clear")
    if not stack:
        prov.status, prov.notes = "unavailable", "no clear summer scenes"
        manifest.add(prov)
        manifest.layer("heat", "unavailable", ["landsat_lst"])
        for a in agebs:
            a["lst"] = None
        return {}

    comp = np.nanmedian(np.stack(stack), axis=0).astype("float32")
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(comp_cache, comp=comp, used=np.array(used))
    return _finish(manifest, agebs, prov, comp, used, transform, w, h)


def _finish(manifest, agebs, prov, comp, used, transform, w, h) -> dict:
    from rasterio.features import rasterize
    from rasterio.warp import transform_geom
    from shapely.geometry import mapping

    # ---- per AGEB ----
    shapes = [(transform_geom("EPSG:4326", UTM, mapping(a["geom"])), i + 1) for i, a in enumerate(agebs)]
    ids = rasterize(shapes, out_shape=(h, w), transform=transform, fill=0, dtype="int32")
    ok = ~np.isnan(comp)
    sums = np.bincount(ids[ok], weights=comp[ok], minlength=len(agebs) + 1)
    cnts = np.bincount(ids[ok], minlength=len(agebs) + 1)
    for i, a in enumerate(agebs):
        a["lst"] = round(float(sums[i + 1] / cnts[i + 1]), 1) if cnts[i + 1] >= 3 else None

    vals = sorted(a["lst"] for a in agebs if a["lst"] is not None)
    urban = comp[(ids > 0) & ok]
    stats = {
        "scenes": used, "n_scenes": len(used), "summers": list(SUMMERS),
        "ageb_min": vals[0], "ageb_max": vals[-1], "ageb_median": float(np.median(vals)),
        "pixel_p95_urban": round(float(np.percentile(urban, 95)), 1),
        "hottest": [{"cvegeo": a["cvegeo"], "lst": a["lst"]} for a in sorted(
            (a for a in agebs if a["lst"] is not None), key=lambda a: -a["lst"])[:3]],
    }

    # ---- picture for close zoom: composite warped to lon/lat, coloured, transparent where empty ----
    _heat_png(comp, transform, stats)

    prov.notes = (f"Mediana por píxel de {len(used)} escenas despejadas ({used[0]} a {used[-1]}), path/row "
                  f"{'/'.join(PATH_ROW)}; nubes y sombras quitadas con QA_PIXEL. Es temperatura del suelo, no del aire.")
    manifest.add(prov)
    manifest.layer("heat", "ok", ["landsat_lst", "nasa_power"])
    print(f"  heat: {len(used)} scenes, barrios {vals[0]}–{vals[-1]} °C")
    return stats


# warm ramp with monotonic lightness (readable in greyscale / colour-blind safe)
RAMP = [(255, 247, 214), (253, 214, 140), (247, 165, 82), (226, 106, 52), (176, 52, 38), (110, 24, 36), (58, 12, 30)]


def _colorize(v: np.ndarray, lo: float, hi: float) -> np.ndarray:
    t = np.clip((v - lo) / (hi - lo), 0, 1) * (len(RAMP) - 1)
    i = np.floor(t).astype(int).clip(0, len(RAMP) - 2)
    f = (t - i)[..., None]
    ramp = np.array(RAMP, dtype="float32")
    return ramp[i] * (1 - f) + ramp[i + 1] * f


def _heat_png(comp, transform, stats):
    from PIL import Image
    from rasterio.enums import Resampling
    from rasterio.transform import from_bounds
    from rasterio.warp import reproject
    w_deg, s, e, n = BBOX[1], BBOX[0], BBOX[3], BBOX[2]
    W = 900
    H = int(W * (n - s) / ((e - w_deg) * np.cos(np.radians(CITY_CENTER[0]))))
    dst = np.full((H, W), np.nan, dtype="float32")
    reproject(comp, dst, src_transform=transform, src_crs=UTM, dst_transform=from_bounds(w_deg, s, e, n, W, H),
              dst_crs="EPSG:4326", resampling=Resampling.bilinear, src_nodata=np.nan, dst_nodata=np.nan)
    # stretch colours to this image's own range (2nd–98th percentile), rounded to whole degrees
    lo, hi = (float(np.floor(np.nanpercentile(dst, 2))), float(np.ceil(np.nanpercentile(dst, 98))))
    rgb = _colorize(np.nan_to_num(dst, nan=lo), lo, hi)
    alpha = np.where(np.isnan(dst), 0, 255)
    Image.fromarray(np.dstack([rgb, alpha]).astype("uint8"), "RGBA").save(OUT / "heat.png", optimize=True)
    stats["image"] = {"file": "heat.png", "bounds": [w_deg, s, e, n], "range": [lo, hi]}
    print(f"  wrote public/data/heat.png ({(OUT / 'heat.png').stat().st_size / 1e6:.2f} MB)")


def build_weather(manifest: Manifest) -> dict:
    """NASA POWER daily max air temperature at the city centre (last 21 days available)."""
    prov = Provenance(id="nasa_power", name="Temperatura máxima diaria del aire (T2M_MAX), centro de " + PLACE,
                      url="https://power.larc.nasa.gov/", license="Dominio público (NASA)", publisher="NASA POWER",
                      vintage="diario, con unos días de retraso", modeled=True,
                      notes="Producto de reanálisis (MERRA-2/GEOS) en celda de ~0.5°; es un valor para toda la ciudad.")
    end = dt.date.fromisoformat(TODAY)
    start = end - dt.timedelta(days=21)
    url = POWER + "?" + urllib.parse.urlencode({
        "parameters": "T2M_MAX", "community": "RE", "latitude": CITY_CENTER[0], "longitude": CITY_CENTER[1],
        "start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"), "format": "JSON", "time-standard": "LST"})
    try:
        d = _json(url)
        series = {k: v for k, v in d["properties"]["parameter"]["T2M_MAX"].items() if v is not None and v > -900}
    except Exception as e:  # noqa: BLE001
        prov.status, prov.notes = "unavailable", str(e)
        manifest.add(prov)
        return {}
    if not series:
        prov.status, prov.notes = "unavailable", "POWER returned only fill values"
        manifest.add(prov)
        return {}
    days = sorted(series)
    iso = lambda k: f"{k[:4]}-{k[4:6]}-{k[6:]}"  # noqa: E731
    last7 = days[-7:]
    hot = max(last7, key=lambda k: series[k])
    manifest.add(prov)
    out = {"latest": {"date": iso(days[-1]), "tmax": round(series[days[-1]], 1)},
           "week_max": {"date": iso(hot), "tmax": round(series[hot], 1)},
           "series": [{"date": iso(k), "tmax": round(series[k], 1)} for k in days]}
    print(f"  weather: latest {out['latest']}, week max {out['week_max']}")
    return out
