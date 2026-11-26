"""The sea (Gulf of California) near the municipio, from Natural Earth 1:10m ocean polygons.

Small-scale data (about 1:10 million), so the shoreline is approximate up close; it is drawn under the
barrios, which keep their own exact INEGI outlines.
"""
from __future__ import annotations

import json

from shapely.geometry import box, mapping, shape

from .common import BBOX, OUT, Manifest, Provenance, SourceUnavailable, fetch, round_coords, write_json

URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_ocean.geojson"
# a bit wider than the map's maxBounds in src/map/MapView.tsx
CLIP = box(BBOX[1] - 0.6, BBOX[0] - 0.4, BBOX[3] + 0.6, BBOX[2] + 0.4)


def build_sea(manifest: Manifest, land=None) -> None:
    """`land` (INEGI municipio outline) is cut out: at 1:10 M the bays near Juan José Ríos spill onto farmland."""
    prov = Provenance(id="naturalearth_ocean", name="Natural Earth — océanos 1:10m", url="https://www.naturalearthdata.com/",
                      license="Dominio público", publisher="Natural Earth", vintage="5.1",
                      notes="Contorno aproximado de la costa (escala 1:10 millones).")
    try:
        p = fetch(URL, "ne_10m_ocean.geojson", max_age_days=365)
        fc = json.loads(p.read_text(encoding="utf-8"))
        parts = []
        for f in fc["features"]:
            g = shape(f["geometry"])
            if not g.intersects(CLIP):
                continue
            g = g.intersection(CLIP)
            if land is not None:
                g = g.difference(land)
            parts.append(g.simplify(0.0008))
        feats = [{"type": "Feature", "geometry": round_coords(mapping(g), 4), "properties": {"kind": "sea"}}
                 for g in parts if not g.is_empty]
        write_json(OUT / "sea.geojson", {"type": "FeatureCollection", "features": feats})
        manifest.layer("sea", "ok", ["naturalearth_ocean"], count=len(feats))
        print(f"  sea: {len(feats)} polygon(s)")
    except (SourceUnavailable, ValueError, KeyError) as e:
        prov.status, prov.notes = "unavailable", str(e)
        manifest.layer("sea", "unavailable", ["naturalearth_ocean"], reason=str(e))
        print(f"  ! sea unavailable: {e}")
    manifest.add(prov)
