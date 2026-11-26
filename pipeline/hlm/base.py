"""Base geometry from INEGI Marco Geoestadístico: AGEBs, blocks, streets.

Two editions:
- December 2025 (live web service), municipio 25-020 Juan José Ríos: the current view.
- Censo 2020 edition (state shapefile zip), Guasave / Ahome localities: the "Antes de ser Municipio" view.
  Juan José Ríos was renumbered when it became a municipio, so 2020 census figures only join to the
  2020 outlines (same CVEGEO), never to the 2025 ones.
"""
from __future__ import annotations

import json

from shapely.geometry import shape, mapping

from .common import ANTES_LOCS, ENT, MUN, OUT, OUT_ANTES, Manifest, Provenance, fetch, local_area_km2, round_coords, write_json

GAIA = "https://gaia.inegi.org.mx/wscatgeo/v2/geo"
MG_LICENSE = "INEGI Términos de libre uso de la información (compatible CC-BY 4.0)"



def _load(url: str, name: str) -> dict:
    return json.loads(fetch(url, name).read_text(encoding="utf-8"))


def load_agebs(manifest: Manifest) -> list[dict]:
    url = f"{GAIA}/agebu/{ENT}/{MUN}"
    gj = _load(url, f"mg2025_agebu_{ENT}{MUN}.json")
    manifest.add(Provenance(
        id="inegi_mg_ageb", name="Marco Geoestadístico — AGEB urbanas", url=url,
        license=MG_LICENSE, publisher="INEGI", vintage=gj.get("metadatos", {}).get(
            "Fuente_informacion_vectorial", "Marco Geoestadístico, diciembre 2025"),
        notes="Boundaries are Dec 2025; census statistics are 2020 and joined by CVEGEO. "
              "AGEBs created after 2020 have no census figures."))
    out = []
    for f in gj["features"]:
        p = f["properties"]
        g = shape(f["geometry"])
        if not g.is_valid:
            g = g.buffer(0)
        out.append({"cvegeo": p["cvegeo"], "loc": p["cve_loc"], "ageb": p["cve_ageb"], "geom": g,
                    "area_km2": local_area_km2(g)})
    print(f"  {len(out)} AGEB geometries")
    return out


def build_blocks(manifest: Manifest, block_pop: dict[str, int | None]):
    url = f"{GAIA}/mza/{ENT}/{MUN}"
    gj = _load(url, f"mg2025_mza_{ENT}{MUN}.json")
    manifest.add(Provenance(id="inegi_mg_mza", name="Marco Geoestadístico — Manzanas", url=url,
                            license=MG_LICENSE, publisher="INEGI", vintage="Marco Geoestadístico, diciembre 2025"))
    _write_blocks(manifest, gj["features"], block_pop, OUT, "blocks")


def _write_blocks(manifest: Manifest, features, block_pop, out_dir, layer):
    feats = []
    for f in features:
        p = f["properties"]
        g = shape(f["geometry"]).simplify(0.00001, preserve_topology=True)
        if g.is_empty:
            continue
        pop = block_pop.get(p["cvegeo"])
        feats.append({"type": "Feature", "geometry": round_coords(mapping(g), 6),
                      "properties": {"id": p["cvegeo"], "pop": pop,
                                     "dens": round(pop / max(local_area_km2(g), 1e-6)) if pop is not None else None}})
    write_json(out_dir / "blocks.geojson", {"type": "FeatureCollection", "features": feats})
    with_pop = sum(f["properties"]["pop"] is not None for f in feats)
    srcs = ["inegi_mg2020" if layer.startswith("antes") else "inegi_mg_mza"] + (["inegi_censo2020"] if with_pop else [])
    manifest.layer(layer, "ok", srcs, count=len(feats), with_pop=with_pop)


def build_streets(manifest: Manifest):
    url = f"{GAIA}/vialidades/{ENT}/{MUN}"
    gj = _load(url, f"mg2025_vialidades_{ENT}{MUN}.json")
    manifest.add(Provenance(id="inegi_mg_vial", name="Marco Geoestadístico — Vialidades", url=url,
                            license=MG_LICENSE, publisher="INEGI", vintage="Marco Geoestadístico, diciembre 2025"))
    major, minor = [], []
    for f in gj["features"]:
        p = f["properties"]
        t = p.get("tipovial") or ""
        name = p.get("nomvial") or ""
        if name in ("Ninguno", "N/A"):
            name = ""
        g = shape(f["geometry"]).simplify(0.00002, preserve_topology=False)
        if g.is_empty:
            continue
        rank = 1 if t in ("Boulevard", "Carretera", "Periférico", "Calzada") else 2 if t == "Avenida" else 3
        feat = {"type": "Feature", "geometry": round_coords(mapping(g), 5),
                "properties": {"r": rank, **({"n": f"{t} {name}".strip()} if name and rank < 3 else {})}}
        (major if rank < 3 else minor).append(feat)
    write_json(OUT / "roads_major.geojson", {"type": "FeatureCollection", "features": major})
    write_json(OUT / "roads_minor.geojson", {"type": "FeatureCollection", "features": minor})
    manifest.layer("roads", "ok", ["inegi_mg_vial"], major=len(major), minor=len(minor))


# ---------- Marco Geoestadístico 2020 (census edition) ----------

MG2020_URL = ("https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/"
              f"geografia/marcogeo/889463807469/{ENT}_" + {"25": "sinaloa"}.get(ENT, ENT) + ".zip")
MG2020_PAGE = "https://www.inegi.org.mx/app/biblioteca/ficha.html?upc=889463807469"


def _mg2020_layer(manifest: Manifest, suffix: str) -> list[dict]:
    """Features of one layer of the 2020 state shapefile ('a' = urban AGEBs, 'm' = blocks), kept to
    ANTES_LOCS and reprojected from INEGI's Lambert conformal conic to lon/lat."""
    import io
    import zipfile

    import shapefile  # pyshp
    from rasterio.crs import CRS
    from rasterio.warp import transform_geom

    path = fetch(MG2020_URL, f"mg2020_{ENT}.zip", max_age_days=3650, timeout=900)
    manifest.add(Provenance(
        id="inegi_mg2020", name="Marco Geoestadístico 2020 (edición del Censo)", url=MG2020_PAGE,
        license=MG_LICENSE, publisher="INEGI", vintage="Censo de Población y Vivienda 2020",
        notes=f"File: {MG2020_URL}. Outlines as they were in 2020, when Juan José Ríos belonged to Guasave "
              "and El Estero to Ahome; they share CVEGEO with the 2020 census tables."))
    base = f"conjunto_de_datos/{ENT}{suffix}"
    with zipfile.ZipFile(path) as z:
        crs = CRS.from_wkt(z.read(base + ".prj").decode("latin-1"))
        r = shapefile.Reader(shp=io.BytesIO(z.read(base + ".shp")), shx=io.BytesIO(z.read(base + ".shx")),
                             dbf=io.BytesIO(z.read(base + ".dbf")), encoding="latin-1")
        names = [f[0] for f in r.fields[1:]]
        out = []
        for sr in r.iterShapeRecords():
            p = dict(zip(names, sr.record))
            if (p["CVE_MUN"], p["CVE_LOC"]) not in ANTES_LOCS:
                continue
            g = shape(transform_geom(crs, "EPSG:4326", sr.shape.__geo_interface__))
            out.append({"properties": {k.lower(): v for k, v in p.items()}, "geom": g if g.is_valid else g.buffer(0)})
    return out


def load_agebs_2020(manifest: Manifest) -> list[dict]:
    out = []
    for f in _mg2020_layer(manifest, "a"):
        p, g = f["properties"], f["geom"]
        out.append({"cvegeo": p["cvegeo"], "loc": p["cve_loc"], "ageb": p["cve_ageb"], "mun": p["cve_mun"],
                    "geom": g, "area_km2": local_area_km2(g)})
    print(f"  {len(out)} AGEB geometries (2020 edition)")
    return out


def build_blocks_2020(manifest: Manifest, block_pop: dict[str, int | None]):
    feats = [{"geometry": mapping(f["geom"]), "properties": f["properties"]} for f in _mg2020_layer(manifest, "m")]
    _write_blocks(manifest, feats, block_pop, OUT_ANTES, "antes_blocks")


CATALOG = "https://gaia.inegi.org.mx/wscatgeo/v2"


def load_municipio(manifest: Manifest):
    """Outline of the municipio (Marco Geoestadístico 2025), used to keep only points inside it."""
    url = f"{GAIA}/mgem/{ENT}/{MUN}"
    gj = _load(url, f"mg2025_mun_{ENT}{MUN}.json")
    manifest.add(Provenance(id="inegi_mg_mun", name="Marco Geoestadístico — Municipio", url=url,
                            license=MG_LICENSE, publisher="INEGI", vintage="Marco Geoestadístico, diciembre 2025"))
    g = shape(gj["features"][0]["geometry"])
    return g if g.is_valid else g.buffer(0)


def locality_names(manifest: Manifest) -> dict[str, str]:
    """Locality names of the municipio from INEGI's catalogue of geostatistical keys (current codes)."""
    url = f"{CATALOG}/localidades/{ENT}/{MUN}"
    try:
        rows = _load(url, f"catalogo_loc_{ENT}{MUN}.json").get("datos", [])
    except Exception as e:  # noqa: BLE001 - names are optional; realms fall back to the code
        print(f"  ! locality names unavailable: {e}")
        return {}
    manifest.add(Provenance(id="inegi_catalogo_loc", name="Catálogo Único de Claves Geoestadísticas — localidades",
                            url=url, license=MG_LICENSE, publisher="INEGI", vintage="2025"))
    return {r["cve_loc"]: r["nomgeo"] for r in rows}
