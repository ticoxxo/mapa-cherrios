"""Verde: vegetation from Sentinel-2 L2A (NDVI) and ESA WorldCover 2021 (tree cover), per AGEB.

Source access: Microsoft Planetary Computer STAC (public; anonymous SAS tokens).

Method
- NDVI now: per-pixel median of clear Sentinel-2 observations in the last WINDOW_DAYS (20 m grid,
  UTM 12N). Clouds, shadows, cirrus and no-data are removed with the scene classification (SCL).
  Reflectance uses the BOA offset (−1000) for processing baseline ≥ 04.00.
- NDVI a year ago: the same window one year earlier, so the change is seasonal-fair.
- Per AGEB: mean NDVI, and % of pixels with NDVI ≥ GREEN_NDVI ("se ve verde").
- Trees: WorldCover 2021 class 10 (tree cover), 10 m. % of each AGEB, and one cartoon tree per 60 m
  cell that is ≥ 25 % tree cover, sized by that spot's NDVI. This is a satellite estimate, not a tree
  inventory (the town has no public one). The UI says so.
"""
from __future__ import annotations

import datetime as dt
import json

import numpy as np

from .common import BBOX, CACHE, OUT, TODAY, Manifest, Provenance, write_json
from .heat import UTM, _json

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
TOKEN = "https://planetarycomputer.microsoft.com/api/sas/v1/token/{}"
WINDOW_DAYS = 30
MAX_CLOUD = 20
RES = 20.0
GREEN_NDVI = 0.3
SCL_BAD = {0, 1, 2, 3, 8, 9, 10}  # no data, saturated, dark/shadow, cloud shadow, clouds, cirrus
TREE_CELL = 6  # 6 × 10 m = 60 m cells for the cartoon trees


def _grid(res: float):
    from rasterio.transform import from_origin
    from rasterio.warp import transform_bounds
    left, bottom, right, top = transform_bounds("EPSG:4326", UTM, BBOX[1], BBOX[0], BBOX[3], BBOX[2])
    left, top = np.floor(left / res) * res, np.ceil(top / res) * res
    return from_origin(left, top, res, res), int(np.ceil((right - left) / res)), int(np.ceil((top - bottom) / res))


def _read(href, transform, w, h, resampling="nearest", nodata=0):
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.vrt import WarpedVRT
    with rasterio.open(href) as src, WarpedVRT(src, crs=UTM, transform=transform, width=w, height=h,
                                                resampling=getattr(Resampling, resampling), nodata=nodata) as vrt:
        return vrt.read(1)


def _search(collection: str, start: dt.date, end: dt.date, query: dict | None = None) -> list[dict]:
    body = {"collections": [collection], "bbox": [BBOX[1], BBOX[0], BBOX[3], BBOX[2]], "limit": 100,
            "datetime": f"{start.isoformat()}T00:00:00Z/{end.isoformat()}T23:59:59Z"}
    if query:
        body["query"] = query
    return _json(STAC, body)["features"]


def _ndvi_composite(start: dt.date, end: dt.date, transform, w, h, token: str):
    import rasterio
    items = _search("sentinel-2-l2a", start, end, {"eo:cloud_cover": {"lt": MAX_CLOUD}})
    stack, used = [], []
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2"):
        for it in sorted(items, key=lambda f: f["properties"]["datetime"]):
            a = it["assets"]
            try:
                scl = _read(f"{a['SCL']['href']}?{token}", transform, w, h)
                if (scl > 0).mean() < 0.05:  # tile barely touches the city window
                    continue
                red = _read(f"{a['B04']['href']}?{token}", transform, w, h, "average").astype("float32")
                nir = _read(f"{a['B08']['href']}?{token}", transform, w, h, "average").astype("float32")
            except Exception as e:  # noqa: BLE001
                print(f"  ! skipped {it['id']}: {e}")
                continue
            off = 1000.0 if str(it["properties"].get("s2:processing_baseline", "00")) >= "04.00" else 0.0
            r, n = (red - off) / 10000, (nir - off) / 10000
            with np.errstate(divide="ignore", invalid="ignore"):
                ndvi = (n - r) / (n + r)
            bad = np.isin(scl, list(SCL_BAD)) | (red == 0) | (nir == 0) | ((n + r) <= 0)
            ndvi[bad] = np.nan
            stack.append(ndvi.astype("float32"))
            used.append(f"{it['properties']['datetime'][:10]} {it['properties']['s2:mgrs_tile']}")
    if not stack:
        return None, []
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return np.nanmedian(np.stack(stack), axis=0).astype("float32"), used


def _worldcover(transform10, w10, h10, token: str):
    import rasterio
    cache = CACHE / "worldcover_2021_10m.npy"
    if cache.exists():
        return np.load(cache)
    items = [f for f in _search("esa-worldcover", dt.date(2021, 1, 1), dt.date(2021, 12, 31)) if "2021" in f["id"]]
    lc = np.zeros((h10, w10), dtype="uint8")
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        for it in items:
            part = _read(f"{it['assets']['map']['href']}?{token}", transform10, w10, h10)
            lc = np.where(lc == 0, part, lc)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(cache, lc)
    return lc


def build_green(manifest: Manifest, agebs: list[dict]) -> dict:
    from rasterio.features import rasterize
    from rasterio.transform import xy
    from rasterio.warp import transform as warp_xy, transform_geom
    from shapely.geometry import mapping

    p_s2 = Provenance(id="sentinel2_ndvi", name="Verdor (NDVI) de los últimos 30 días y de hace un año",
                      url="https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a",
                      license="Copernicus Sentinel data (uso libre con atribución)",
                      publisher="Copernicus / ESA — Sentinel-2 (vía Microsoft Planetary Computer)", vintage="últimos 30 días")
    p_wc = Provenance(id="esa_worldcover", name="ESA WorldCover 2021 (cobertura de árboles, 10 m)",
                      url="https://planetarycomputer.microsoft.com/dataset/esa-worldcover", license="CC-BY 4.0",
                      publisher="ESA WorldCover consortium", vintage="2021", modeled=True,
                      notes="Clasificación por satélite; los árboles dibujados son un indicador, no un inventario.")
    end = dt.date.fromisoformat(TODAY)
    start = end - dt.timedelta(days=WINDOW_DAYS)
    try:
        # SAS tokens expire (about an hour): ask for a fresh one right before each long read
        tok = lambda c: _json(TOKEN.format(c))["token"]  # noqa: E731
        T, w, h = _grid(RES)
        now, used_now = _ndvi_composite(start, end, T, w, h, tok("sentinel-2-l2a"))
        ago, used_ago = _ndvi_composite(start.replace(year=start.year - 1), end.replace(year=end.year - 1), T, w, h,
                                        tok("sentinel-2-l2a"))
        T10, w10, h10 = _grid(10.0)
        lc = _worldcover(T10, w10, h10, tok("esa-worldcover"))
    except Exception as e:  # noqa: BLE001
        p_s2.status, p_s2.notes = "unavailable", str(e)
        manifest.add(p_s2)
        manifest.layer("green", "unavailable", ["sentinel2_ndvi", "esa_worldcover"], reason=str(e))
        for a in agebs:
            a.update(ndvi=None, p_green=None, ndvi_ago=None, p_tree=None)
        return {}
    if now is None:
        p_s2.status, p_s2.notes = "unavailable", "no clear Sentinel-2 scenes in the last 30 days"
        manifest.add(p_s2)
        manifest.layer("green", "unavailable", ["sentinel2_ndvi"])
        for a in agebs:
            a.update(ndvi=None, p_green=None, ndvi_ago=None, p_tree=None)
        return {}

    def zonal(transform, ww, hh):
        shapes = [(transform_geom("EPSG:4326", UTM, mapping(a["geom"])), i + 1) for i, a in enumerate(agebs)]
        return rasterize(shapes, out_shape=(hh, ww), transform=transform, fill=0, dtype="int32")

    def mean_by(ids, arr, mask=None):
        ok = ~np.isnan(arr) if mask is None else mask
        s = np.bincount(ids[ok], weights=arr[ok].astype("float64"), minlength=len(agebs) + 1)
        c = np.bincount(ids[ok], minlength=len(agebs) + 1)
        return s, c

    ids20 = zonal(T, w, h)
    s_now, c_now = mean_by(ids20, now)
    green = (now >= GREEN_NDVI).astype("float32")
    s_green, _ = mean_by(ids20, green, ~np.isnan(now))
    s_ago, c_ago = mean_by(ids20, ago) if ago is not None else (None, None)
    ids10 = zonal(T10, w10, h10)
    tree = (lc == 10).astype("float32")
    s_tree, c_10 = mean_by(ids10, tree, lc > 0)
    for i, a in enumerate(agebs):
        k = i + 1
        a["ndvi"] = round(float(s_now[k] / c_now[k]), 3) if c_now[k] >= 3 else None
        a["p_green"] = round(float(100 * s_green[k] / c_now[k]), 1) if c_now[k] >= 3 else None
        a["ndvi_ago"] = round(float(s_ago[k] / c_ago[k]), 3) if s_ago is not None and c_ago[k] >= 3 else None
        a["p_tree"] = round(float(100 * s_tree[k] / c_10[k]), 1) if c_10[k] >= 5 else None

    # ---- cartoon trees: one per 60 m cell that is ≥ 25 % tree cover, inside barrios ----
    H6, W6 = h10 // TREE_CELL, w10 // TREE_CELL
    tc = tree[:H6 * TREE_CELL, :W6 * TREE_CELL].reshape(H6, TREE_CELL, W6, TREE_CELL).mean(axis=(1, 3))
    inside = (ids10[:H6 * TREE_CELL, :W6 * TREE_CELL].reshape(H6, TREE_CELL, W6, TREE_CELL) > 0).any(axis=(1, 3))
    rows, cols = np.nonzero((tc >= 0.25) & inside)
    xs, ys = xy(T10, rows * TREE_CELL + TREE_CELL / 2, cols * TREE_CELL + TREE_CELL / 2, offset="ul")
    lons, lats = warp_xy(UTM, "EPSG:4326", list(np.atleast_1d(xs)), list(np.atleast_1d(ys)))
    # NDVI at each tree (20 m grid)
    inv = ~T
    feats = []
    for lon, lat, x, y, frac in zip(lons, lats, np.atleast_1d(xs), np.atleast_1d(ys), tc[rows, cols]):
        c, r = inv * (x, y)
        v = now[int(r), int(c)] if 0 <= int(r) < h and 0 <= int(c) < w else np.nan
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
                      "properties": {"v": None if np.isnan(v) else round(float(v), 2), "c": round(float(frac), 2)}})
    write_json(OUT / "trees.geojson", {"type": "FeatureCollection", "features": feats})

    city = ids20 > 0
    vals_now = now[city & ~np.isnan(now)]
    stats = {
        "window": [start.isoformat(), end.isoformat()], "scenes_now": used_now, "scenes_ago": used_ago,
        "city_ndvi": round(float(vals_now.mean()), 3),
        "city_p_green": round(float(100 * (vals_now >= GREEN_NDVI).mean()), 1),
        "city_ndvi_ago": round(float(np.nanmean(ago[city])), 3) if ago is not None else None,
        "city_p_tree": round(float(100 * tree[(ids10 > 0) & (lc > 0)].mean()), 1),
        "n_trees": len(feats),
    }
    p_s2.notes = (f"Mediana por píxel de {len(used_now)} pasadas despejadas ({start} a {end}); "
                  f"hace un año: {len(used_ago)} pasadas. Nubes quitadas con la clasificación SCL.")
    p_s2.vintage = f"{start} a {end}"
    manifest.add(p_s2)
    manifest.add(p_wc)
    manifest.layer("green", "ok", ["sentinel2_ndvi", "esa_worldcover"])
    print(f"  green: {len(used_now)} passes now, {len(used_ago)} a year ago; city NDVI {stats['city_ndvi']} "
          f"(was {stats['city_ndvi_ago']}); {stats['city_p_tree']}% tree cover; {len(feats)} trees drawn")
    return stats
